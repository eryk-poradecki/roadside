/**
 * The driver's own details for the damage report (ADR 0009). They never reach the server:
 * they fill the letter's placeholders only when it is copied, and the stored body keeps the
 * placeholders. "Remember on this device" keeps them in this browser's localStorage.
 */
export interface Claimant {
  name: string
  address: string
  phone: string
  bankAccount: string
}

export const EMPTY_CLAIMANT: Claimant = { name: '', address: '', phone: '', bankAccount: '' }

/**
 * The placeholders the backend's letter templates use, in both languages
 * (`backend/app/assist/letters/`). The addressee stays a placeholder: the driver looks it up.
 */
const PLACEHOLDERS: Record<keyof Claimant, readonly string[]> = {
  name: ['[Your name]', '[Imię i nazwisko]'],
  address: ['[Your address]', '[Adres]'],
  phone: ['[Your phone]', '[Telefon]'],
  bankAccount: ['[Your bank account]', '[Numer konta bankowego]'],
}

const FIELDS = Object.keys(PLACEHOLDERS) as (keyof Claimant)[]

/** The letter with every claimant placeholder whose detail is filled in replaced by it. */
export function fillClaimant(body: string, claimant: Claimant): string {
  let filled = body
  for (const field of FIELDS) {
    const value = claimant[field].trim()
    if (!value) continue
    for (const placeholder of PLACEHOLDERS[field]) filled = filled.replaceAll(placeholder, value)
  }
  return filled
}

const STORAGE_KEY = 'roadside.claimant'

const isClaimant = (value: unknown): value is Claimant =>
  typeof value === 'object' &&
  value !== null &&
  FIELDS.every((f) => typeof (value as Record<string, unknown>)[f] === 'string')

/** The details remembered on this device, or null. Never throws: storage may be blocked. */
export function loadClaimant(): Claimant | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return null
    const parsed: unknown = JSON.parse(raw)
    return isClaimant(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function rememberClaimant(claimant: Claimant): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(claimant))
  } catch {
    // Blocked storage: the details still work for this visit.
  }
}

export function forgetClaimant(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Nothing was stored.
  }
}
