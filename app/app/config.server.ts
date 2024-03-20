import { PrismaClient } from "@prisma/client"
import { Inngest } from "inngest"
import { Configuration, OpenAIApi } from "openai-edge"

export const db = new PrismaClient()

export const inngest = new Inngest({
  name: "Meaning Assistant",
  apiKey: process.env.INNGEST_API_KEY,
})

export const openai = new OpenAIApi(new Configuration({
  apiKey: process.env.OPENAI_API_KEY,
}))

export const cardModel: "mgg" | "dft" = "mgg"