import type { LoaderFunctionArgs, MetaFunction} from "@remix-run/node";
import { redirect } from "@remix-run/node"

export const meta: MetaFunction = () => {
  return [
    { title: "Graph Explorer" },
    { name: "description", content: "See a graph" },
  ]
}

export async function loader({ request }: LoaderFunctionArgs) {
  return redirect("/graph")
}
