import { DeduplicatedCard } from "@prisma/client"
import { useEffect, useRef } from "react"
import ValuesCard from "./cards/values-card"

type CardWithCounts = DeduplicatedCard

export default function Carousel({ cards }: { cards: CardWithCounts[] }) {
  const carouselRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let position = 0
    const scrollAmount = 10
    const transitionSpeed = 1000

    const interval = setInterval(() => {
      if (carouselRef.current) {
        position += scrollAmount
        carouselRef.current.style.transform = `translateX(-${position}px)`
        carouselRef.current.style.transition = `transform ${transitionSpeed}ms linear`
      }
    }, transitionSpeed)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative z-0 w-[200%] mx-[-50%] overflow-x-hidden">
      <div ref={carouselRef} className="flex hide-scrollbar space-x-4">
        {cards.map((card) => (
          <div key={card.id} className="flex flex-col">
            <div className="flex-grow w-96">
              <ValuesCard card={card} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
