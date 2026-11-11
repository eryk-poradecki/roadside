import {
  EMPTY_CLAIMANT,
  fillClaimant,
  forgetClaimant,
  loadClaimant,
  rememberClaimant,
  type Claimant,
} from './claimant'

const JAN: Claimant = {
  name: 'Jan Kowalski',
  address: 'ul. Długa 1, 00-001 Warszawa',
  phone: '+48 600 100 200',
  bankAccount: 'PL61 1090 1014 0000 0712 1981 2874',
}

const PL_BODY = `[Imię i nazwisko]
[Adres]
Tel.: [Telefon]

[Adresat: zarządca drogi]

Proszę przelać na rachunek: [Numer konta bankowego].

[Imię i nazwisko]`

describe('fillClaimant', () => {
  it('fills every claimant placeholder of a Polish letter, each time it appears', () => {
    expect(fillClaimant(PL_BODY, JAN)).toBe(`Jan Kowalski
ul. Długa 1, 00-001 Warszawa
Tel.: +48 600 100 200

[Adresat: zarządca drogi]

Proszę przelać na rachunek: PL61 1090 1014 0000 0712 1981 2874.

Jan Kowalski`)
  })

  it('fills the English placeholders too', () => {
    const body = '[Your name], [Your address], [Your phone], [Your bank account]'

    expect(fillClaimant(body, JAN)).toBe(
      'Jan Kowalski, ul. Długa 1, 00-001 Warszawa, +48 600 100 200, PL61 1090 1014 0000 0712 1981 2874',
    )
  })

  it('keeps the placeholder of a detail left empty', () => {
    expect(fillClaimant('[Your name] / [Your phone]', { ...EMPTY_CLAIMANT, name: ' Jan ' })).toBe(
      'Jan / [Your phone]',
    )
  })

  it('never touches the addressee placeholder', () => {
    expect(fillClaimant('[Addressee: road manager]', JAN)).toBe('[Addressee: road manager]')
  })
})

describe('remembering the details on this device', () => {
  it('loads nothing until the driver asks to remember', () => {
    expect(loadClaimant()).toBeNull()
  })

  it('round-trips through localStorage and can be forgotten', () => {
    rememberClaimant(JAN)
    expect(loadClaimant()).toEqual(JAN)

    forgetClaimant()
    expect(loadClaimant()).toBeNull()
  })

  it('ignores a malformed entry', () => {
    localStorage.setItem('roadside.claimant', '{"name": 1}')
    expect(loadClaimant()).toBeNull()
  })

  it('works when storage is blocked', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    try {
      expect(loadClaimant()).toBeNull()
    } finally {
      spy.mockRestore()
    }
  })
})
