import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import MoralGraph from "~/components/moral-graph";
import type { MoralGraph as MoralGraphType } from "~/routes/api.graph";

function LoadingScreen() {
  return <div className="h-screen w-full mx-auto flex items-center justify-center">
    <Loader2 className="h-4 w-4 animate-spin" />
  </div>
}

export default function DefaultGraphPage() {
  const [graph, setGraph] = useState<MoralGraphType | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!graph && !isLoading) {
      setIsLoading(true)
      fetchData()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph, isLoading])

  const fetchData = async () => {
    try {
      const res = await fetch('/api/graph')
      const { graph } = await res.json()
      setGraph(graph)
      setIsLoading(false)
    } catch {
      setIsLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'row' }}>
      <div className="flex-grow">
        {isLoading || !graph ? <LoadingScreen /> : <MoralGraph graph={graph} />}
      </div>
    </div>
  )
}
