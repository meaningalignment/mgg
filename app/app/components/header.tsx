import { useCurrentUser, useCurrentUserSpaces } from "../root"
import { Button } from "./ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu"
import { Form, Link } from "@remix-run/react"
import { useRef } from "react"
import { ChevronDown, User as UserIcon } from "lucide-react"
import type { Collection, User } from "@prisma/client"
import type { SerializeFrom } from "@remix-run/node"

function UserMenu({ user }: { user: User }) {
  const formRef = useRef(null)

  const handleSubmit = () => {
    const ref = formRef.current as any
    ref?.submit()
  }

  return (
    <div className="flex items-center justify-between">
      <Form method="post" action="/auth/logout" ref={formRef}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="pl-0">
              <span className="ml-2 hidden md:block">{user?.email}</span>
              <div className="flex items-center justify-center pl-4 w-full md:hidden">
                <UserIcon className="h-5 w-5" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            sideOffset={8}
            align="start"
            className="w-[200px]"
          >
            <Link to="/profile">
              <DropdownMenuItem className="cursor-pointer">
                Your Profile
              </DropdownMenuItem>
            </Link>

            <DropdownMenuSeparator />
            <DropdownMenuItem className="cursor-pointer" onClick={handleSubmit}>
              <button>Sign Out</button>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </Form>
    </div>
  )
}

export default function Header() {
  const user = useCurrentUser()
  const spaces = useCurrentUserSpaces()

  return (
    <header className="sticky top-0 z-50 flex items-center w-full h-16 px-4 border-b shrink-0 bg-gradient-to-b from-background/10 via-background/50 to-background/80 backdrop-blur-md dark:bg-black dark:from-black dark:via-black dark:to-black border-gray-200 dark:border-gray-700 gap-x-4">
      <div className="flex items-baseline w-full">
        {user ? <>
          <Link to={`/notes/${user.username}`}>
            <Button variant="ghost" className="ml-2 px-2">
              Your notes
            </Button>
          </Link>

          {spaces ? <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="ml-2 px-2">
                Your spaces
                <ChevronDown className="h-4 w-4 ml-1" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {
                spaces.sort((a, b) => a.name.localeCompare(b.name)).map(c => (
                  <Link key={c.id} to={`/space/${c.id}`}>
                    <DropdownMenuItem className="cursor-pointer">
                      {c.name}
                    </DropdownMenuItem>
                  </Link>
                ))
              }
              {spaces.length > 0 && <DropdownMenuSeparator />}
              <DropdownMenuItem asChild className="cursor-pointer">
                <Link to="/space/new">New space...</Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
            : null}

        </> : null}
        <div className="flex-grow" />
        <div className="flex items-center justify-end">
          {user ? <UserMenu user={user} /> : <Link to="/auth/login">
            <Button variant="ghost">
              Log in
            </Button>
          </Link>}
        </div>
      </div>
    </header>
  )
}

export function SpaceHeader({ collection }: { collection: SerializeFrom<Collection> }) {
  const user = useCurrentUser()

  return (
    <header className="sticky top-0 z-50 flex items-center w-full h-16 px-4 border-b shrink-0 bg-gradient-to-b from-background/10 via-background/50 to-background/80 backdrop-blur-md dark:bg-black dark:from-black dark:via-black dark:to-black border-gray-200 dark:border-gray-700 gap-x-4">
      <div className="flex items-baseline w-full">
        <Link to={`/space/${collection!.id}`} className="flex items-center md:mr-4">
          <h1 className="md:ml-2 font-bold">{collection.name}</h1>
        </Link>
        <div className="flex-grow" />
        <div className="flex items-center justify-end">
          {user ? <UserMenu user={user} /> : <Link to="/auth/login">
            <Button variant="ghost">
              Log in
            </Button>
          </Link>}
        </div>
      </div>
    </header>
  )
}