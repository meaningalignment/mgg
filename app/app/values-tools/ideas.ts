import type { ChatCompletionFunctions } from "openai-edge"
import { definitionOfASourceOfMeaning } from "./prompt-segments"
import { put } from "@vercel/blob"
import type {
  IdeaGenerationStatus,
  ValuesCard,
  Share,
  User,
  PinnedIdea,
} from "@prisma/client"
import { db, inngest, openai } from "~/config.server"
import OpenAI from "openai"
import axios from "axios"
import { pseudonymousValues } from "~/lib/consts"

interface Idea {
  title: string
  description: string
  participants: string[]
}

interface Person {
  name: string | null
  email: string
}

export type AugmentedShare = Pick<Share, "userId"> & {
  user: Pick<User, "id" | "email" | "name">
  valuesCard: Pick<
    ValuesCard,
    | "title"
    | "instructionsShort"
    | "instructionsDetailed"
    | "evaluationCriteria"
  >
}

export const minValuesForIdeaGen = 3

function sourceAsText(
  source: Pick<
    ValuesCard,
    | "title"
    | "instructionsShort"
    | "instructionsDetailed"
    | "evaluationCriteria"
  >
) {
  return `"${source.title}"\n${source.instructionsShort}\n(${
    source.instructionsDetailed
  })\nAttending to:${source.evaluationCriteria.map((c) => `\n- ${c}`).join("")}`
}

function sourcesDictionary(shares: AugmentedShare[]) {
  const byUserId: { [key: string]: AugmentedShare[] } = {}
  shares.forEach((share) => {
    const userId = share.user.id
    if (!byUserId[userId]) byUserId[userId] = []
    byUserId[userId].push(share)
  })
  const sources = Object.entries(byUserId).map(([userId, shares]) => {
    const person = { name: shares[0].user.name, email: shares[0].user.email }
    return { person, sources: shares.map((share) => share.valuesCard) }
  })
  return sources
    .map(
      (s) =>
        `### Sources for ${s.person.name || s.person.email} (email: ${
          s.person.email
        }): \n\n${s.sources.map((som) => sourceAsText(som)).join("\n\n")}`
    )
    .join("\n\n")
}

const ideasForOthersPrompt = `
You are an expert event designer. I'll give a list of people, and for each person, one or more "sources of meaning" that are important to them. Your job is to design events that the people could do with each other, {{TIMEFRAME}}.

# Who to design for

Your job is to design events for 2 or 3 people at a time, based on their sources of meaning – the things they find it most meaningful to pay attention to in life.

# About Your Events

The point of the event designs, is to make it easier for someone to attend to their source of meaning. So, only include designs that:
- Make the source of meaning easier to attend to, by removing distractions.
- Make the information in the source of meaning easier to find, by surfacing it.
- Make the source of meaning easier to choose by, by making it more salient or less taboo.
- Identify some other hard part of attending to the source of meaning, and making it easier.

# How to describe the events
- The event idea descriptions should be 1-2 sentences long. For example: "A TV station break-in, in which Anne has the gun and Joe does the seduction.".
- Prefer noun phrases to verbs.
- Don't say why the idea is good.
- In each idea description, give an important detail that makes it easier to attend to the source of meaning. (Just give the detail, don't say why it helps.)

# Definition of a source of meaning
${definitionOfASourceOfMeaning}`

const ideasPrompt = `
You are an expert event designer. I'll give a list of people, and for each person, one or more "sources of meaning" that are important to them. You'll be talking to {{NAME}} -- one of the people. Your job is to design events that {{NAME}} could do with the others, {{TIMEFRAME}}.

# Who to design for

Your job is to design events for 2 or 3 people at a time, including {{NAME}}, based on their sources of meaning – the things they find it most meaningful to pay attention to in life.

# About Your Events

The point of the event designs, is to make it easier for someone to attend to their source of meaning. So, only include designs that:
- Make the source of meaning easier to attend to, by removing distractions.
- Make the information in the source of meaning easier to find, by surfacing it.
- Make the source of meaning easier to choose by, by making it more salient or less taboo.
- Identify some other hard part of attending to the source of meaning, and making it easier.

# How to describe the events
- The event idea descriptions should be 1-2 sentences long. For example: "A TV station break-in, in which Anne has the gun and Joe does the seduction.".
- Prefer noun phrases to verbs.
- Don't say why the idea is good.
- In each idea description, give an important detail that makes it easier to attend to the source of meaning. (Just give the detail, don't say why it helps.)

# Definition of a source of meaning
${definitionOfASourceOfMeaning}`

const submitIdeasFunction: ChatCompletionFunctions = {
  name: "submit_ideas",
  description: "Submit ideas for events based on the input.",
  parameters: {
    type: "object",
    properties: {
      events: {
        type: "array",
        description: "The event ideas to submit. Should not be longer than 6.",
        items: {
          type: "object",
          description: "An event idea to submit.",
          properties: {
            title: {
              type: "string",
              description: "A short title of the event idea.",
            },
            description: {
              type: "string",
              description: "The event idea to submit.",
            },
            participants: {
              type: "array",
              description:
                "The email addresses of the participants in the event.",
              items: {
                type: "string",
                description: "An email address to one event participant.",
              },
            },
          },
        },
      },
    },
    required: ["events"],
  },
}

export async function generateIdeas(
  timeframe: string,
  shares: AugmentedShare[],
  mainPerson: Person
) {
  let prompt: string

  if (!shares.find((s) => s.user.email === mainPerson.email)) {
    prompt = ideasForOthersPrompt.replace(/{{TIMEFRAME}}/g, timeframe)
  } else {
    const mainPersonName = mainPerson.name || mainPerson.email
    prompt = ideasPrompt
      .replace(/{{NAME}}/g, mainPersonName)
      .replace(/{{TIMEFRAME}}/g, timeframe)
  }

  const dictionary = sourcesDictionary(shares)

  const result = await openai.createChatCompletion({
    model: "gpt-4-1106-preview",
    messages: [
      { role: "system", content: prompt },
      { role: "user", content: dictionary },
    ],
    temperature: 0.4,
    stream: false,
    functions: [submitIdeasFunction],
    function_call: { name: submitIdeasFunction.name },
  })

  const data = await result.json()
  const ideas = JSON.parse(data.choices[0].message.function_call.arguments)
    .events as Idea[]

  return ideas
}

export async function generateIdeaImage(idea: string): Promise<string> {
  //
  // The current version of the dall-e API apparently thinks "An intimate gathering with friends" is too sexy 🤦‍♂️
  //
  // Dirty workaround to not bump into content policy errors all the time.
  // Can remove and pass idea as-is when API is improved.
  //
  const result = await openai.createChatCompletion({
    model: "gpt-3.5-turbo",
    messages: [
      {
        role: "system",
        content:
          "Make sure the image prompt passed to you passes all content guidelines. Return a modified, child-friendly version.",
      },
      { role: "user", content: idea },
    ],
  })

  const data = await result.json()
  const unsexifiedIdea = data.choices[0].message.content

  //
  // Generate the image.
  //
  const openaiApi = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  const response = await openaiApi.images.generate({
    model: "dall-e-3",
    prompt: unsexifiedIdea,
    n: 1,
    size: "1024x1024",
  })

  // This image url is temporary. To make it permanent, we need to save it to the Vercel blob store.
  console.log("Generated temporary image url for idea.")
  return response.data[0].url!
}

export async function saveToBlobStore(imageUrl: string, imageName: string) {
  const response = await axios.get(imageUrl, { responseType: "stream" })
  const stream = response.data
  const fileName = `idea-images/${imageName}.png`

  console.log(`Uploading image ${imageName} to blob store.`)

  const { url } = await put(fileName, stream, { access: "public" })

  console.log(`Uploaded image ${imageName}.`)

  return url
}

async function addIdeasToDatabase(
  ideas: Idea[],
  userId: number,
  collectionId: number,
  shares: AugmentedShare[]
): Promise<PinnedIdea[]> {
  return await Promise.all(
    ideas.map(async (idea) => {
      const ideaDb = await db.pinnedIdea.create({
        data: {
          title: idea.title,
          description: idea.description,
          collectionId,
          userId,
        },
      })

      await db.ideaParticipants.createMany({
        data: idea.participants.map((p) => ({
          participantId: shares.find((s) => s.user.email === p)!.user.id,
          pinnedIdeaId: ideaDb.id,
        })),
      })

      return ideaDb
    })
  )
}

function createPseudonymousShares(
  yourValue: ValuesCard
) {
  const shares = pseudonymousValues.map((v, i) => {
    return {
      userId: i,
      user: {
        id: i,
        name: pseudonymousValues[i].user,
        email: pseudonymousValues[i].user.toLowerCase() + "@acme.com",
      },
      valuesCard: {
        title: v.title,
        instructionsShort: v.instructionsShort,
        instructionsDetailed: v.instructionsShort,
        evaluationCriteria: v.evaluationCriteria,
      },
    }
  }) as AugmentedShare[]

  const you = {
    id: pseudonymousValues.length,
    name: "You",
    email: "you@acme.com",
  }

  // Append your value to the list of values.
  shares.push({
    userId: you.id,
    user: you,
    valuesCard: yourValue,
  } as AugmentedShare)

  return { shares, you }
}

export async function startIdeaGeneration(
  userId: number,
  collectionId: number
): Promise<Boolean> {
  const shareCount = await db.share.count({ where: { collectionId } })
  if (shareCount < minValuesForIdeaGen) {
    console.log(
      `Not enough values to generate ideas for user ${userId} and collection ${collectionId}.`
    )
    return false
  }

  const ideaGen = await db.ideaGeneration.findUnique({
    where: { userId_collectionId: { userId, collectionId } },
  })

  if (ideaGen?.state === "running") {
    console.log("Idea generation already running.")
    return false
  }

  // Stage the idea generation.
  await db.ideaGeneration.upsert({
    where: { userId_collectionId: { userId, collectionId } },
    create: { userId, collectionId, state: "pending" },
    update: { state: "pending", inngestRunId: null },
  })

  // Start generating ideas in the background.
  await inngest.send({
    name: "ideas/generate",
    data: { userId, collectionId },
  })

  return true
}

export async function startOnboardingIdeaGeneration(
  valuesCardId: number
): Promise<Boolean> {
  const ideaGen = await db.onboardingIdeaGeneration.findUnique({
    where: { valuesCardId },
  })

  if (ideaGen?.state === "running") {
    console.log("Idea generation already running.")
    return false
  }

  // Stage the idea generation.
  await db.onboardingIdeaGeneration.upsert({
    where: { valuesCardId },
    create: { valuesCardId, state: "pending" },
    update: { state: "pending", inngestRunId: null },
  })

  // Start generating ideas in the background.
  await inngest.send({
    name: "onboarding-ideas/generate",
    data: { valuesCardId },
  })

  return true
}

export const ideas = inngest.createFunction(
  {
    name: "Generate ideas for user",
    onFailure: async ({ error, event, step }) => {
      const { collectionId, userId } = event.data.event.data

      await step.run("Update run status to failed", async () => {
        return await db.ideaGeneration.update({
          where: { userId_collectionId: { userId, collectionId } },
          data: { state: "failed" },
        })
      })

      return { message: `Failed to generate ideas for user ${userId}`, error }
    },
  },
  { event: "ideas/generate" },
  async ({ event, step, logger, runId }) => {
    const { collectionId, userId } = event.data

    if (!collectionId || !userId) {
      throw new Error(
        `Missing collectionId or userId in event data: ${JSON.stringify(
          event.data
        )}`
      )
    }

    const status = (await step.run("Get run status", async () => {
      return await db.ideaGeneration
        .findUnique({
          where: { userId_collectionId: { userId, collectionId } },
        })
        .then((d) => d?.state)
    })) as IdeaGenerationStatus

    if (status === "running") {
      return {
        message: `Ideas are already being generated for user ${userId} and collection ${collectionId}.`,
      }
    }

    await step.run("Update run status to running", async () => {
      return await db.ideaGeneration.upsert({
        where: { userId_collectionId: { userId, collectionId } },
        update: { state: "running", inngestRunId: runId },
        create: { userId, collectionId, state: "running", inngestRunId: runId },
      })
    })

    //
    // Get relevant data.
    //
    const user = (await step.run("Get user", async () => {
      return (await db.user.findUnique({ where: { id: userId } })) as Person
    })) as User

    const shares = (await step.run("Get shares", async () => {
      return (await db.share.findMany({
        where: { collectionId },
        include: { user: true, valuesCard: true },
      })) as AugmentedShare[]
    })) as any as AugmentedShare[]

    const timeframe = (await step.run("Get timeframe", async () => {
      return await db.collection
        .findUnique({ where: { id: collectionId } })
        .then((d) => d?.ideasTimeframe)
    })) as string

    //
    // Generate ideas.
    //
    const ideas = (await step.run("Generate ideas", async () => {
      return await generateIdeas(timeframe, shares, user)
    })) as Idea[]

    await step.run("Add ideas to database", async () => {
      return addIdeasToDatabase(ideas, userId, collectionId, shares)
    })

    //
    // Generate images.
    //
    // There seems to be a problem with saving images to the blob store.
    // For now, we'll ignore images.
    //
    // const images = await step.run("Generate images", async () => {
    //   return await Promise.all(
    //     ideas.map(async (idea) => {
    //       return await generateIdeaImage(idea.description)
    //     })
    //   )
    // })

    // await step.run("Add images to database", async () => {
    //   return await Promise.all(
    //     images.map(async (image, index) => {
    //       const imageUrl = await saveToBlobStore(
    //         image,
    //         ideasDb[index].id.toString()
    //       )

    //       return await db.pinnedIdea.update({
    //         where: { id: ideasDb[index].id },
    //         data: { imageUrl },
    //       })
    //     })
    //   )
    // })

    await step.run("Update run status to done", async () => {
      return await db.ideaGeneration.update({
        where: { userId_collectionId: { userId, collectionId } },
        data: { state: "done", inngestRunId: runId },
      })
    })

    const message = `Generated ${ideas.length} ideas with images for user ${userId} and collection ${collectionId}.`
    logger.info(message)
    return { message }
  }
)

export const onboardingIdeas = inngest.createFunction(
  {
    name: "Generate ideas for the onboarding flow",
    onFailure: async ({ error, event, step }) => {
      const { valuesCardId } = event.data.event.data

      await step.run("Update run status to failed", async () => {
        return await db.onboardingIdeaGeneration.update({
          where: { valuesCardId: valuesCardId },
          data: { state: "failed" },
        })
      })

      return {
        message: `Failed to generate ideas for values card ${valuesCardId}`,
        error,
      }
    },
  },
  { event: "onboarding-ideas/generate" },
  async ({ event, step, logger, runId }) => {
    const { valuesCardId } = event.data

    if (!valuesCardId) {
      throw new Error(
        `Missing valuesCardId in event data: ${JSON.stringify(event.data)}`
      )
    }

    //
    // Prepare the run.
    //
    const status = (await step.run("Get run status", async () => {
      return await db.onboardingIdeaGeneration
        .findUnique({ where: { valuesCardId: valuesCardId } })
        .then((d) => d?.state)
    })) as IdeaGenerationStatus

    if (status === "running") {
      return {
        message: `Onboarding ideas are already being generated for user ${valuesCardId}.`,
      }
    }

    await step.run("Update run status to running", async () => {
      return await db.onboardingIdeaGeneration.upsert({
        where: { valuesCardId: valuesCardId },
        update: { state: "running", inngestRunId: runId },
        create: { valuesCardId, state: "running", inngestRunId: runId },
      })
    })

    //
    // Get relevant data.
    //
    const yourValue = (await step.run("Get your value", async () => {
      return await db.valuesCard.findUnique({
        where: { id: valuesCardId },
      })
    })) as any as ValuesCard

    //
    // Generate ideas.
    //
    const result = await step.run("Generate ideas", async () => {
      const { shares, you } = createPseudonymousShares(yourValue)
      const ideas = await generateIdeas("later today", shares, you)
      return ideas.filter((i) => i.participants.includes(you.email))
    })

    await step.run("Update run status to done, and save ideas.", async () => {
      return await db.onboardingIdeaGeneration.update({
        where: { valuesCardId: valuesCardId },
        data: { state: "done", inngestRunId: runId, result },
      })
    })

    const message = `Generated ideas for valuesCard ${valuesCardId}.`
    logger.info(message)
    return { message }
  }
)
