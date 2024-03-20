export type DftValuesCardModel = {
  id: number
  title: string
  instructionsShort: string
  instructionsDetailed: string
  evaluationCriteria: string[]
}

export type MggValuesCardModel = {
  id: number
  title: string
  policies: string[]
}

export type ValuesCardModel = DftValuesCardModel | MggValuesCardModel