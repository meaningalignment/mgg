import { Link } from "@remix-run/react"
import React from "react"
import { cn } from "~/utils"

export function DatePerhapsAsLink({ date, toUrl }: { date: string, toUrl?: string }) {
  if (!toUrl) return <div className="text-sm text-gray-600 dark:text-gray-400">
    {new Date(date).toLocaleDateString()}
  </div>
  return <Link to={toUrl} className="text-sm text-gray-600 dark:text-gray-400 hover:underline">
    {new Date(date).toLocaleDateString()}
  </Link>
}

export function Grid({ children }: { children: React.ReactNode[] }) {
  const childCount = React.Children.count(children)

  return <div className="grid flex-grow place-items-center space-y-8 py-12">
    <div className={cn("grid mx-auto gap-6 lg:gap-y-8",
      childCount >= 3 ? "xl:grid-cols-3" : "",
      childCount >= 2 ? "lg:grid-cols-2" : "",
    )}>
      {children}
    </div>
  </div>
}

export function TightGrid({ children }: { children: React.ReactNode[] }) {
  const childCount = React.Children.count(children)
  
  return <div className="grid flex-grow place-items-center space-y-8 py-12">
    <div className={cn("grid mx-auto gap-6 lg:gap-y-8",
      childCount >= 3 ? "lg:grid-cols-3" : "",
      childCount >= 2 ? "md:grid-cols-2" : "",
    )}>
      {children}
    </div>
  </div>
}