import { serve } from "inngest/remix"
import { inngest } from "~/config.server"
import { embed } from "~/values-tools/embedding"
import { deduplicate, seedGeneration } from "~/values-tools/deduplicator"

const handler = serve(inngest, [seedGeneration, deduplicate, embed])

export const config = {
  maxDuration: 300,
}

export { handler as loader, handler as action }
