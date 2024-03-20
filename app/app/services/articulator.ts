import type { Chat, ValuesCard } from "@prisma/client"
import type { ChatCompletionRequestMessage } from "openai-edge/types/api"
import type {
  ArticulatorConfig
} from "../values-tools/articulator-config";
import {
  metadata,
  summarize,
} from "../values-tools/articulator-config"
import type { ValuesCardData } from "~/lib/consts"
import { OpenAIStream } from "~/lib/openai-stream"
import { capitalize } from "~/utils"
import { embeddingService } from "~/values-tools/embedding"
import { articulatorConfigs, db, openai } from "~/config.server"

// import { OpenAIStream, StreamingTextResponse } from "ai"   TODO replace the above import with this once https://github.com/vercel-labs/ai/issues/199 is fixed.

interface ArticulatorSettings {
  promptTask: string
  promptSubmitStep: string
}

type ArticulateCardResponse = {
  values_card: ValuesCardData
  critique?: string | null
}

type FunctionResult = {
  message: string | null
  articulatedCard: ValuesCardData | null
  submittedCard: ValuesCardData | null
}

export function normalizeMessage(
  message: ChatCompletionRequestMessage
): ChatCompletionRequestMessage {
  // only role, content, name, function_call
  const { role, content, name, function_call } = message
  if (function_call && !function_call.arguments) function_call.arguments = "{}"
  return { role, content, name, function_call }
}

/**
 * A service for handling function calls in the chat.
 */
export class ArticulatorService {
  public config: ArticulatorConfig
  public settings: ArticulatorSettings

  constructor(configKey: string, settings: ArticulatorSettings) {
    this.settings = settings
    this.config = articulatorConfigs[configKey]
  }

  metadata() {
    return metadata(this.config)
  }

  // TODO: put it in a transaction
  private async addServerSideMessage({
    chatId,
    messages,
    message,
    data,
  }: {
    chatId: string
    messages: ChatCompletionRequestMessage[]
    message: ChatCompletionRequestMessage
    data?: {
      provisionalCard?: ValuesCardData
      provisionalCanonicalCardId?: number | null
    }
  }) {
    messages.push(message)
    const chat = await db.chat.findUnique({
      where: { id: chatId },
    })
    const transcript = (chat?.transcript ??
      []) as any as ChatCompletionRequestMessage[]
    transcript.push(message)
    await db.chat.update({
      where: { id: chatId },
      data: {
        transcript: transcript as any,
        ...data,
      },
    })
  }

  async processCompletionWithFunctions({
    userId,
    messages,
    function_call,
    chatId,
    collectionId,
  }: {
    userId: number
    messages: ChatCompletionRequestMessage[]
    function_call: { name: string } | null
    chatId: string
    collectionId: number | null
  }) {
    // update the db
    // TODO: put it in a transaction
    const chat = await db.chat.findUnique({ where: { id: chatId } })
    if (chat) {
      const transcript = (chat?.transcript ??
        []) as any as ChatCompletionRequestMessage[]
      const lastMessage = messages[messages.length - 1]
      transcript.push(lastMessage)
      messages = transcript.map((o) => normalizeMessage(o))
      await db.chat.update({
        where: { id: chatId },
        data: {
          transcript: transcript as any,
        },
      })
    } else {
      const metadata = this.metadata()
      // Prepend the system message.
      let mainPrompt = this.config.prompts.main.prompt
      mainPrompt = mainPrompt.replace("{{TASK}}", this.settings.promptTask)
      mainPrompt = mainPrompt.replace(
        "{{SUBMIT_STEP}}",
        this.settings.promptSubmitStep
      )

      messages = [{ role: "system", content: mainPrompt }, ...messages]
      await db.chat.create({
        data: {
          id: chatId,
          transcript: messages as any,
          userId,
          articulatorModel: metadata.model,
          articulatorPromptHash: metadata.contentHash,
          articulatorPromptVersion: metadata.name,
          gitCommitHash: metadata.gitHash,
        },
      })
    }

    // Only include the submit function if a card has already been articulated and shown to the user.
    // This prevents submit from being called before the user has articulated a card, which causes an error.
    let functions = this.config.prompts.main.functions
    if (chat && !chat.provisionalCard) {
      functions = functions.filter((f) => f.name !== "submit_values_card")
    }

    const completionResponse = await openai.createChatCompletion({
      model: this.config.model,
      messages: messages,
      temperature: 0.7,
      stream: true,
      functions,
      function_call: function_call ?? "auto",
    })

    if (!completionResponse.ok) return { completionResponse }

    // Get any function call that is present in the stream.
    const functionCall = await this.getFunctionCall(completionResponse)
    if (!functionCall) return { completionResponse }

    // If a function call is present in the stream, handle it...
    await this.addServerSideMessage({
      chatId,
      messages,
      message: {
        role: "assistant",
        content: null as any,
        function_call: {
          name: functionCall.name,
          arguments: JSON.stringify(functionCall.arguments),
        },
      },
    })
    const { response, articulatedCard, submittedCard } = await this.handle(
      functionCall,
      messages,
      chatId,
      collectionId
    )
    return {
      functionCall,
      response,
      articulatedCard,
      submittedCard,
      completionResponse,
    }
  }

  //
  // Vercel AI openai functions handling is broken in Remix. The `experimental_onFunctionCall` provided by the `ai` package does not work.
  //
  // We have to handle them manually, until https://github.com/vercel-labs/ai/issues/199 is fixed.
  // This is done by listening to the first token and seeing if it is a function call.
  // If so, wait for the whole response and handle the function call.
  // Otherwise, return the stream as-is.
  //
  async getFunctionCall(
    res: Response
  ): Promise<{ name: string; arguments: object } | null> {
    const stream = OpenAIStream(res.clone()) // .clone() since we don't want to consume the response.
    const reader = stream.getReader()

    //
    // In the case of a function call, the first token in the stream
    // is an unfinished JSON object, with "function_call" as the first key.
    //
    // We can use that key to check if the response is a function call.
    //
    const { value: first } = await reader.read()

    const isFunctionCall = first
      ?.replace(/[^a-zA-Z0-9_]/g, "")
      ?.startsWith("function_call")

    if (!isFunctionCall) {
      return null
    }

    //
    // Function arguments are streamed as tokens, so we need to
    // read the whole stream, concatenate the tokens, and parse the resulting JSON.
    //
    let result = first

    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        break
      }

      result += value
    }

    //
    // Return the resulting function call.
    //
    const json = JSON.parse(result)["function_call"]
    console.log(`Function call: ${JSON.stringify(json)}`)

    // The following is needed due to tokens being streamed with escape characters.
    json["arguments"] = JSON.parse(json["arguments"])
    console.log(`Function call: ${JSON.stringify(json)}`)
    return json as { name: string; arguments: object }
  }

  private async handleArticulateCardFunction(
    chatId: string,
    messages: ChatCompletionRequestMessage[]
  ): Promise<FunctionResult> {
    //
    // Fetch the chat with the provisional card from the database.
    //
    const chat = (await db.chat.findUnique({
      where: { id: chatId },
    }))!

    const previousCard = chat.provisionalCard
      ? (chat.provisionalCard as ValuesCardData)
      : null

    // Articulate the values card.
    const response = await this.articulateValuesCard(messages, previousCard)

    // The newly articulated card.
    let newCard = response.values_card

    //
    // If the card is not yet meeting the guidelines, generate a follow-up question.
    //
    if (response.critique) {
      const message = summarize(this.config, "show_values_card_critique", {
        critique: response.critique,
      })

      return {
        message,
        articulatedCard: null,
        submittedCard: null,
      }
    }


    await this.addServerSideMessage({
      chatId,
      messages,
      message: {
        role: "function",
        name: "show_values_card",
        content: JSON.stringify(response.values_card),
      },
      data: {
        provisionalCard: newCard!,
      },
    })

    const message = summarize(this.config, "show_values_card", {
      title: newCard!.title,
    })
    return { message, articulatedCard: newCard, submittedCard: null }
  }

  private async handleSubmitCardFunction(
    chatId: string,
    collectionId: number | null
  ): Promise<FunctionResult> {
    const chat = (await db.chat.findUnique({
      where: { id: chatId },
    })) as Chat

    const card = chat.provisionalCard as ValuesCardData

    // Submit the values card.
    const message = await this.submitValuesCard(
      card,
      chatId,
      chat.userId,
      collectionId,
      chat.provisionalCanonicalCardId
    )

    return { message, submittedCard: card, articulatedCard: null }
  }

  async handle(
    func: { name: string; arguments: any },
    messages: any[] = [],
    chatId: string,
    collectionId: number | null
  ): Promise<{
    response: Response
    articulatedCard: ValuesCardData | null
    submittedCard: ValuesCardData | null
  }> {
    let functionResult: FunctionResult

    switch (func.name) {
      case "guess_values_card": {
        console.log("Guessed!", func.arguments)
        functionResult = {
          message: null,
          articulatedCard: null,
          submittedCard: null,
        }
        break
      }
      case "show_values_card": {
        functionResult = await this.handleArticulateCardFunction(
          chatId,
          messages
        )
        break
      }
      case "submit_values_card": {
        functionResult = await this.handleSubmitCardFunction(
          chatId,
          collectionId
        )
        break
      }
      default: {
        throw new Error("Unknown function call: " + func.name)
      }
    }

    if (functionResult.message) {
      console.log(`Result from "${func.name}":\n${functionResult.message}`)

      await this.addServerSideMessage({
        chatId,
        messages,
        message: {
          role: "function",
          name: func.name,
          content: functionResult.message,
        },
      })
    }

    //
    // Call the OpenAI API with the function result.
    //
    // This wraps the raw function result in a generated message that fits the flow
    // of the conversation.
    //

    console.log(`Calling OpenAI API with function result...`)
    console.log(`Messages:\n${JSON.stringify(messages)}`)

    const response = await openai.createChatCompletion({
      model: this.config.model,
      messages,
      temperature: 0.0,
      functions: this.config.prompts.main.functions,
      function_call: "none", // Prevent recursion.
      stream: true,
    })

    return { response, ...functionResult }
  }

  async submitValuesCard(
    card: ValuesCardData,
    chatId: string,
    userId: number,
    collectionId: number | null,
    canonicalCardId: number | null
  ): Promise<string> {
    console.log(`Submitting values card:\n\n${JSON.stringify(card)}`)

    // Save the card in the database.
    const result = (await db.valuesCard
      .create({
        data: {
          title: card.title,
          instructionsShort: card.instructions_short,
          instructionsDetailed: card.instructions_detailed,
          evaluationCriteria: card.evaluation_criteria,
          chatId,
          canonicalCardId: canonicalCardId ?? null,
          shares: collectionId
            ? { create: { collectionId, userId } }
            : undefined,
        },
      })
      .catch((e) => console.error(e))) as ValuesCard

    // Embed card.
    await embeddingService.embedNonCanonicalCard(result)
    return summarize(this.config, "submit_values_card", { title: card.title })
  }

  /** Create a values card from a transcript of the conversation. */
  async articulateValuesCard(
    messages: ChatCompletionRequestMessage[],
    previousCard: ValuesCardData | null
  ): Promise<ArticulateCardResponse> {
    console.log("Articulating values card...")

    let transcript = messages
      .filter((m) => m.role === "assistant" || m.role === "user")
      .map((m) => `${capitalize(m.role)}: ${m.content}`)
      .join("\n")

    if (previousCard) {
      transcript += `Previous card: ${JSON.stringify(previousCard)}`
    }

    const res = await openai.createChatCompletion({
      model: this.config.model,
      messages: [
        {
          role: "system",
          content: this.config.prompts.show_values_card.prompt,
        },
        { role: "user", content: transcript },
      ],
      functions: this.config.prompts.show_values_card.functions,
      function_call: { name: "format_card" },
      temperature: 0.0,
      stream: false,
    })

    const data = await res.json()
    const response = JSON.parse(
      data.choices[0].message.function_call.arguments
    ) as ArticulateCardResponse

    return response
  }
}
