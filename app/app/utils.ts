import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import crypto from 'crypto'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(input: string | number | Date): string {
  const date = new Date(input)
  return date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

export function capitalize(input: string): string {
  return input.split(" ").map((word) => word[0].toUpperCase() + word.slice(1)).join(" ")
}

export function isAllUppercase(str: string) {
  if (str === "I") return false
  return str === str.toUpperCase()
}

/**
 * Calculate the average embedding vector.
 * @param embeddings An array of embedding vectors.
 * @returns The average embedding vector.
 */
export function calculateAverageEmbedding(embeddings: number[][]): number[] {
  if (embeddings.length === 0) {
    throw new Error("The embeddings array cannot be empty")
  }

  const dimension = embeddings[0].length

  // Ensure all vectors have the same dimension
  for (let emb of embeddings) {
    if (emb.length !== dimension) {
      throw new Error("All embedding vectors should have the same dimension")
    }
  }

  let averageVector = Array(dimension).fill(0)

  // Sum up all embedding vectors
  for (let emb of embeddings) {
    for (let i = 0; i < dimension; i++) {
      averageVector[i] += emb[i]
    }
  }

  // Divide by the number of embedding vectors to get the average
  for (let i = 0; i < dimension; i++) {
    averageVector[i] /= embeddings.length
  }

  return averageVector
}

export function splitToPairs<T>(arr: T[]): T[][] {
  return (
    Array.from({ length: Math.ceil(arr.length / 2) }, (_, i) =>
      arr.slice(i * 2, i * 2 + 2)
    ).filter((p) => p.length == 2) ?? []
  )
}

export function isDisplayableMessage(message: {
  role: string
  content?: string
}) {
  return (
    message?.content &&
    (message.role === "user" || message.role === "assistant")
  )
}

export function withTransition(
  show: boolean,
  delay: number,
  className?: string
): string {
  return cn(
    "transition-opacity ease-in duration-500",
    show ? "opacity-100" : "opacity-0",
    `delay-${delay}`,
    className ? className : ""
  )
}

export function nValues(n: number) {
  return n === 1 ? "1 value" : `${n} values`
}

export function nIdeas(n: number) {
  if (n === 0) return "No ideas yet"
  return n === 1 ? "1 idea" : `${n} ideas`
}

export function nSpaces(n: number) {
  if (n === 0) return "No spaces yet"
  return n === 1 ? "1 space" : `${n} spaces`
}

export function generateToken(length: number) {
  return crypto.randomBytes(length).toString('base64url');
}


export function timeAgo(date: Date): string {
  const now = new Date()
  const seconds = Math.round((now.getTime() - date.getTime()) / 1000)
  const minutes = Math.round(seconds / 60)
  const hours = Math.round(minutes / 60)
  const days = Math.round(hours / 24)
  const weeks = Math.round(days / 7)
  const months = Math.round(days / 30)
  const years = Math.round(days / 365)

  if (seconds < 60) {
    return "Just now"
  } else if (minutes < 60) {
    return `${minutes} minute${minutes > 1 ? "s" : ""} ago`
  } else if (hours < 24) {
    return `${hours} hour${hours > 1 ? "s" : ""} ago`
  } else if (days < 7) {
    return `${days} day${days > 1 ? "s" : ""} ago`
  } else if (weeks < 5) {
    return `${weeks} week${weeks > 1 ? "s" : ""} ago`
  } else if (months < 12) {
    return `${months} month${months > 1 ? "s" : ""} ago`
  } else {
    return `${years} year${years > 1 ? "s" : ""} ago`
  }
}