/** Navigation state the help sheet sets when it opens the Result for a new incident. */
export const FROM_HELP = { fromHelp: true } as const

export const isFromHelp = (state: unknown) =>
  typeof state === 'object' && state !== null && 'fromHelp' in state
