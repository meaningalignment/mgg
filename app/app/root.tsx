import { cssBundleHref } from "@remix-run/css-bundle"
import {
  json,
  SerializeFrom,
  type LinksFunction,
  type LoaderFunctionArgs,
} from "@remix-run/node"
import {
  Links,
  LiveReload,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useRouteLoaderData,
} from "@remix-run/react"
import styles from "./tailwind.css"
import { auth, db } from "./config.server"
import { TooltipProvider } from "@radix-ui/react-tooltip"
import { User } from "@prisma/client"
import { Toaster } from "react-hot-toast"
import { Analytics } from "@vercel/analytics/react"
import React from "react"

export const links: LinksFunction = () => [
  ...(cssBundleHref ? [{ rel: "stylesheet", href: cssBundleHref }] : []),
  { rel: "stylesheet", href: styles },
]

export async function loader({ request }: LoaderFunctionArgs) {
  const userId = await auth.getUserId(request)

  const user =
    userId &&
    ((await db.user.findUnique({
      where: { id: userId },
    })) as User | null)

  const values =
    userId ?
      (await db.valuesCard.findMany({ where: { chat: { userId } } })) : null

  const spaces = userId ? (await db.collection.findMany({
    where: {
      OR: [
        {
          shares: {
            some: {
              userId,
            }
          }
        },
        {
          createdById: userId,
        }
      ]
    },
    include: { shares: true }
  })) : null

  return json({ user, values, spaces })
}

export function useCurrentUser(): User | null {
  const { user } = useRouteLoaderData("root") as SerializeFrom<typeof loader>
  return user
}

export function useCurrentUserValues() {
  const { values } = useRouteLoaderData("root") as SerializeFrom<typeof loader>
  return values
}

export function useCurrentUserSpaces() {
  const { spaces } = useRouteLoaderData("root") as SerializeFrom<typeof loader>
  return spaces
}

export default function App() {
  return (
    <TooltipProvider>
      <html lang="en">
        <head>
          <meta charSet="utf-8" />
          <meta name="viewport" content="width=device-width,initial-scale=1" />
          <Meta />
          <Links />
        </head>
        <body className="bg-slate-50 dark:bg-neutral-900 text-black dark:text-gray-200">
          <Outlet />
          <React.Suspense>
            <Toaster />
          </React.Suspense>
          <ScrollRestoration />
          <Scripts />
          <LiveReload />
          <Analytics />
        </body>
      </html>
    </TooltipProvider>
  )
}
