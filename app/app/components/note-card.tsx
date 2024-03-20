/* eslint-disable jsx-a11y/alt-text */
import { LockClosedIcon } from "@radix-ui/react-icons"
import { Form, Link, useSearchParams, useSubmit } from "@remix-run/react"
import { Copy, Edit, Lock, LockIcon, Reply } from "lucide-react"
import { useState } from "react"
import remarkGfm from "remark-gfm"
import ValuesCard from "~/components/cards/values-card"
import { MemoizedReactMarkdown } from "~/components/markdown"
import { Button } from "~/components/ui/button"
import { Dialog, DialogContent, DialogTrigger } from "~/components/ui/dialog"
import { useCurrentUser } from "~/root"
import type { Note } from "~/routes/_.notes.$username.$noteUuid._index"

const clients = [
  {
    id: "gpt-aa",
    name: "Astra Aesthetica GPT",
    url: "https://chat.openai.com/g/g-jIE3A8aSa-astra-aesthetica",
  },
  {
    id: "gpt-values",
    name: "Values Discovery GPT",
    url: "https://chat.openai.com/g/g-TItg5klMA-values-discovery",
  }
]

export function ShareDialog({ children }: { children: React.ReactNode }) {
  const url = 'window' in globalThis ? window.location.href : ""
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 1000)
  }
  return (
    <Dialog>
      <DialogTrigger>
        {children}
      </DialogTrigger>
      <DialogContent>
        <h1 className="text-2xl font-bold">Share this note</h1>
        <p className="mt-1 mb-2">
          Copy this link and share it with someone else.
        </p>
        <div className="flex flex-row items-center">
          <input className="border border-gray-300 dark:border-gray-700 rounded p-2 w-full" value={url} readOnly />
          <Button size="icon" variant="ghost" onClick={copy}>
            <Copy className="w-4 h-4" />
          </Button>
        </div>
        {copied && <span className="text-sm text-gray-400 ml-1">Copied!</span>}
      </DialogContent>
    </Dialog>
  )
}

function ImagePlaceholder() {
  return (
    <div className="bg-gray-300 dark:bg-gray-700 w-32 h-32 rounded-md" />
  )
}

function CloudinaryImageUploadPlaceholder({ item, defaultImageUrl }: { item: string, defaultImageUrl?: string }) {
  const [image, setImage] = useState<File | null>(null)
  const imageUploading = image
  const submit = useSubmit()
  return (
    <label>
      <input
        className="hidden"
        form="nonExistentForm"
        type="file"
        accept="image/*"
        onChange={async (e) => {
          const file = e.target.files!.item(0)!
          setImage(file)
          const data = new FormData()
          data.append("file", file)
          data.append("upload_preset", "pf3mos3z")
          try {
            const res = await fetch("https://api.cloudinary.com/v1_1/meaning-supplies/image/upload", {
              method: "POST",
              body: data,
            })
            const json = await res.json()
            submit({
              item,
              imageUrl: json.secure_url as string
            }, {
              method: "post",
              replace: true,
            })
          } catch (e) {
            setImage(null)
            alert("Error uploading image. Maybe try a smaller size.")
            console.error(e)
          }
        }}
      />
      {!image && !defaultImageUrl && <ImagePlaceholder />}
      {!image && defaultImageUrl && <img src={defaultImageUrl} className="w-32 h-32 rounded-md" alt="Appreciation" />}
      {image && (
        <img
          className={`mt-2 ${imageUploading ? "animate-pulse" : ""}`}
          src={URL.createObjectURL(image)}
          width={100}
        />
      )}
    </label>
  )
}


// an image thumbnail that, when clicked, opens the image in a modal
function ImageThumbnail({ src }: { src: string }) {
  return (
    <Dialog>
      <DialogTrigger className="cursor-pointer">
        <img src={src} className="w-32 h-32 rounded-md mt-1" />
      </DialogTrigger>
      <DialogContent className="flex flex-col items-center justify-center">
        <img src={src} />
      </DialogContent>
    </Dialog>
  )
}

function CopyToClipboard({ children }: { children: string }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 1000)
  }
  return (
    <>
      <code className={"bg-gray-200 dark:bg-gray-800 dark:text-gray-300 px-1 py-0.5 rounded-md ml-1 text-sm text-gray-500" + (copied ? " animate-pulse" : "")} onClick={copy} title="Copy to clipboard">{children}</code>
      <Button variant="link" size="icon" onClick={copy}>
        <Copy className="w-4 h-4 ml-1 text-gray-400 hover:text-gray-500" />
      </Button>
      {copied && <span className="text-sm text-gray-400 ml-1">Copied!</span>}
    </>
  )
}

function ReplyDialog({ note }: { note: Note }) {
  const [params, setParams] = useSearchParams()
  const user = useCurrentUser()
  const redirectUrl = `/notes/@${note.user?.username}/${note.uuid}?reply=${note.uuid}}`
  const noteAuthorName = note.user?.name || note.user?.username
  function onOpenChange(open: boolean) {
    setParams((prev) => {
      if (open) {
        return new URLSearchParams({ ...prev, reply: note.uuid })
      } else {
        const newParams = new URLSearchParams(prev)
        newParams.delete("reply")
        return newParams
      }
    })
  }
  return <Dialog defaultOpen={params.get("reply") === note.uuid} onOpenChange={onOpenChange}>
    <DialogTrigger>
      <Button variant="secondary" size="sm" >
        <Reply className="w-4 h-4 mr-2" />
        Reply
      </Button>
    </DialogTrigger>
    <DialogContent>
      <h1 className="text-2xl font-bold">Reply to {note.user?.name || note.user?.username}</h1>
      <p className="mt-1 mb-2">
        {/* instructions */}
        In this note, {noteAuthorName} describes a certain kind of beauty. Can you find something with the same kind of beauty?
      </p>
      {user ? <p className="mt-1 mb-2">
        <b>To reply:</b> Copy this note ID <CopyToClipboard>{note.uuid}</CopyToClipboard>. <a target="_blank" className="hover:underline text-blue-500" href="https://chat.openai.com/g/g-jIE3A8aSa-astra-aesthetica" rel="noreferrer">Launch our GPT</a>, and paste the note ID into the chat. The GPT will interview you about the beauty you found, and set up the reply.
      </p> : <p className="mt-1 mb-2">
        <b>To reply:</b> First, <a target="_blank" className="hover:underline text-blue-500" href={`/auth/login?redirect=${encodeURIComponent(redirectUrl)}`} rel="noreferrer">log in</a> or create an account. Then, you'll get a link to our GPT, which will record your description of the beauty you found. ({noteAuthorName} will get a notification when you reply.)
      </p>}
    </DialogContent>
  </Dialog>
}

export function NoteEditor({ note }: { note: Note }) {
  const author = note.user
  const image = note.body.match(/!\[.*\]\((.*)\)/)
  const imageUrl = image ? image[1] : undefined
  const authorLink = <Link to={`/notes/@${author?.username}`}>{author?.name || author?.username}</Link>

  return (
    <Form className="flex flex-col mx-auto max-w-md" method="post">
      <div className="flex flex-row items-center">
        <div className="flex-grow">
          <h1 className="text-3xl font-bold">
            <input className="w-full" defaultValue={note.title} name="title" />
          </h1>
          <h4 className="text-sm text-gray-500 dark:text-gray-400">
            An {note.type} by {authorLink}
          </h4>
        </div>
      </div>

      <div className="flex flex-row mt-2">
        <div>
          <CloudinaryImageUploadPlaceholder item={note.uuid} defaultImageUrl={imageUrl} />
        </div>
        <div className="flex flex-col ml-4">
          <textarea className="border border-gray-300 dark:border-gray-700 rounded p-2 w-full h-28" name="body" defaultValue={note.body} />
        </div>
      </div>
      <select className="border border-gray-300 dark:border-gray-700 rounded p-2 w-full mt-2" name="visibility" defaultValue={note.visibility}>
        <option value="public">Public</option>
        <option value="unlisted">Unlisted</option>
      </select>
      <Button type="submit" className="mt-2">Save</Button>
    </Form>
  )
}


export function NoteCard({ note, isNoteAuthor, link, hideAuthor }: { note: Note, isNoteAuthor: boolean, link?: boolean, hideAuthor?: boolean }) {
  const card = note.valuesCard
  const author = note.user
  const createdAt = new Date(note.createdAt).toLocaleDateString()
  const image = note.body.match(/!\[.*\]\((.*)\)/)
  const bodyWithoutImage = note.body.replace(/!\[.*\]\((.*)\)/, "")
  const imageUrl = image ? image[1] : undefined
  const authorLink = author && <Link
    className="hover:underline"
    to={`/notes/@${author?.username}`}
  >{author?.name || author?.username}
  </Link>
  const client = clients.find(c => c.id === note.clientId)

  return (
    <div className="flex flex-col mx-auto max-w-sm md:max-w-md px-2">
      <div className="flex flex-row items-baseline gap-2">
        <div className="flex-grow">
          <h1 className="text-2xl font-semibold">
            {note.visibility === "unlisted" && <LockClosedIcon className="w-3 h-3 mr-1 inline" />}
            {link ? <Link to={`/notes/@${author?.username}/${note.uuid}`} className="hover:underline">
              {note.title || "Untitled"}
            </Link> : note.title || "Untitled"}
            {!link && isNoteAuthor && <Link to={`./edit`}>
              <Button size="icon" variant="link">
                <Edit className="w-4 h-4 ml-2 text-gray-400" />
              </Button>
            </Link>}
          </h1>
          {!hideAuthor && <h4 className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            An {note.type} by {authorLink || "Anonymous"}
          </h4>}
        </div>
        <ReplyDialog note={note} />
      </div>

      <div className="flex flex-row mt-3 gap-4 items-start">
        {imageUrl ?
          <ImageThumbnail src={imageUrl} /> :
          isNoteAuthor ?
            <CloudinaryImageUploadPlaceholder item={note.uuid} /> : null}
        <div className="flex flex-col flex-shrink">
          <div className="mb-4 ">
            <MemoizedReactMarkdown
              className="prose break-words dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 max-w-sm"
              remarkPlugins={[remarkGfm]}
              components={{
                p({ children }) {
                  return <p className="mb-2 last:mb-0 text-gray-600 dark:text-gray-300">{children}</p>
                },
              }}
            >
              {bodyWithoutImage}
            </MemoizedReactMarkdown>
            <div className="text-gray-400 text-xs mr-3 mt-2 uppercase">
              {createdAt} {client && <>• via <a href={client.url} target="_blank" className="underline hover:text-gray-500" rel="noreferrer">{client.name}</a></>}
            </div>
          </div>
          <div className="self-end max-w-[340px]">
            <ValuesCard card={card as any} detailsInline />
            <div className="flex flex-row items-center justify-end mt-1 text-gray-400 text-sm mr-3 hover:underline">
              <Link to={`/vision/${card.id}?valueAuthorId=${note.userId}`}>
                Learn about this value →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

