import React, { useState } from "react"
import { useChat, type Message } from "ai/react"
import { cn } from "../../utils"
import { ChatList } from "./chat-list"
import { ChatPanel } from "./chat-panel"
import { EmptyScreen } from "../layout/empty-screen"
import { ChatScrollAnchor } from "./chat-scroll-anchor"
import { toast } from "react-hot-toast"
import type { ValuesCardData } from "~/lib/consts"

export interface ChatProps extends React.ComponentProps<"div"> {
  initialMessages?: Message[]
  hasSubmitted?: boolean
  chatId: string,
  collectionId: number | null,
  articulatorConfig?: string,
}

export function Chat({
  chatId,
  collectionId,
  initialMessages,
  hasSubmitted,
  className,
  articulatorConfig = "default",
}: ChatProps) {
  const [valueCards, setValueCards] = useState<
    { position: number; card: ValuesCardData }[]
  >([])
  const [isFinished, setIsFinished] = useState(hasSubmitted || false)

  const onCardArticulation = (card: ValuesCardData) => {
    console.log("Card articulated:", card)

    setValueCards((prev) => [
      ...prev,
      {
        // The last user & assistant pair has not been appended yet.
        position: messages.length + 1,
        card,
      },
    ])
  }

  const onCardSubmission = (card: ValuesCardData) => {
    console.log("Card submitted:", card)

    setIsFinished(true)
  }

  const onManualSubmit = () => {
    append(
      {
        role: "user",
        content: "Submit Card",
      },
      {
        function_call: {
          name: "submit_values_card",
          arguments: ""
        },
      }
    )
  }

  const { messages, append, reload, stop, isLoading, input, setInput } =
    useChat({
      id: chatId,
      api: "/api/chat-completion",
      headers: {
        "X-Articulator-Config": articulatorConfig,
        "Content-Type": "application/json",
      },
      body: {
        chatId: chatId,
        collectionId,
      },
      initialMessages,
      onResponse: async (response) => {
        const articulatedCard = response.headers.get("X-Articulated-Card")
        if (articulatedCard) {
          onCardArticulation(JSON.parse(articulatedCard) as ValuesCardData)
        }

        const submittedCard = response.headers.get("X-Submitted-Card")
        if (submittedCard) {
          onCardSubmission(JSON.parse(submittedCard) as ValuesCardData)
        }

        if (response.status === 401) {
          console.error(response.status)
          toast.error("Failed to update chat. Please try again.")
        }
      },
      onError: async (error) => {
        console.error(error)
        toast.error("Failed to update chat. Please try again.")

        //
        // Delete any lingering function call messages.
        // 
        const deletionResponse = await fetch(`/api/chat/${chatId}/function`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        })
        const deletionBody = await deletionResponse.json()
        console.log(`Deleted function calls: ${JSON.stringify(deletionBody)}`)

        //
        // Get the last message from the database and set it as the input.
        //
        const messageResponse = await fetch(`/api/messages/${chatId}`)
        const messageJson = await messageResponse.json()

        if (messageJson && messageJson.messages) {
          const messages = messageJson.messages as Message[]
          const lastMessage = messages[messages.length - 1]

          console.log("messages:", messages)
          console.log("lastMessage:", lastMessage)

          if (lastMessage.role === "user") {
            setInput(lastMessage.content)
          }
        }
      },
      onFinish: async (message) => {
        console.log("Chat finished:", message)
        console.log("messages:", messages)

        // Save messages in the database.
        await fetch(`/api/messages/${chatId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            chatId: chatId,
            messages: [
              ...messages,
              {
                role: "user",
                content: input,
              },
              message,
            ],
          }),
        })
      },
    })

  return (
    <>
      <div className={cn("pb-[200px] pt-4 md:pt-10", className)}>
        {messages.length ? (
          <>
            <ChatList
              chatId={chatId}
              messages={messages}
              isFinished={isFinished}
              isLoading={isLoading}
              valueCards={valueCards}
              onManualSubmit={onManualSubmit}
            />
            <ChatScrollAnchor trackVisibility={isLoading} />
          </>
        ) : (
          <>
            <EmptyScreen />
          </>
        )}
      </div>
      <ChatPanel
        id={chatId}
        collectionId={collectionId}
        isLoading={isLoading}
        isFinished={isFinished}
        stop={stop}
        append={append}
        reload={reload}
        messages={messages}
        input={input}
        setInput={setInput}
      />
    </>
  )
}
