import { screen, waitFor, within } from '@testing-library/react'
import { ADVICE, fakeApi } from './fakeApi'
import { renderApp } from './render'

const photosPanel = () => screen.getByRole('region', { name: 'Photos' })
const resultPanel = () => screen.findByRole('region', { name: 'Photos' })
const aiPanel = () => screen.getByRole('region', { name: 'Personalised steps' })

/** A deferred promise: holds every photo upload until the test releases it. */
function holdUploads() {
  let release = () => {}
  fakeApi.photoGate = new Promise<void>((resolve) => {
    release = resolve
  })
  return () => {
    fakeApi.photoGate = null
    release()
  }
}

const photo = (name: string) => new File([`bytes of ${name}`], name, { type: 'image/jpeg' })

async function openSheet(tile = 'Pothole damage') {
  const { user } = renderApp('/')
  await user.click(await screen.findByRole('button', { name: tile }))
  const sheet = await screen.findByRole('dialog', { name: tile })
  return { user, sheet }
}

beforeEach(() => {
  // jsdom makes no object URLs; the sheet previews picked files with them.
  URL.createObjectURL = vi.fn(() => 'blob:preview')
  URL.revokeObjectURL = vi.fn()
})

describe('photos in the help sheet', () => {
  it('demo mode offers sample photos instead of a file picker', async () => {
    const { user, sheet } = await openSheet()

    expect(
      within(sheet).getByText('Uploads are off in demo mode. Pick a sample photo instead.'),
    ).toBeInTheDocument()
    expect(within(sheet).queryByLabelText('Add photos')).not.toBeInTheDocument()

    await user.click(within(sheet).getByRole('button', { name: 'Flat front tyre' }))
    await user.click(within(sheet).getByRole('button', { name: 'Deep pothole in the road' }))
    expect(within(sheet).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(2)

    // Removed one by one before sending.
    await user.click(within(sheet).getByRole('button', { name: 'Remove photo 1' }))
    expect(within(sheet).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(1)

    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    expect(
      await within(await resultPanel()).findByRole('img', { name: 'Photo 1' }),
    ).toBeInTheDocument()
    expect(fakeApi.photoRequests).toEqual([{ incidentId: 1, sampleId: 'pothole' }])
    expect(within(photosPanel()).getByText('1 of 5')).toBeInTheDocument()
  })

  it('uploads picked files one per request after the incident is created', async () => {
    fakeApi.config = { demo_mode: false, vision_enabled: false }
    const { user, sheet } = await openSheet()

    await user.upload(within(sheet).getByLabelText('Add photos'), [photo('a.jpg'), photo('b.jpg')])
    expect(within(sheet).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(2)
    expect(fakeApi.photoRequests).toEqual([])

    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    const panel = await resultPanel()
    await waitFor(() => {
      expect(within(panel).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(2)
    })
    // jsdom can't decode images, so the files go up as they are, as multipart. (The name
    // is lost between jsdom and Node's fetch; the server never uses it anyway.)
    expect(fakeApi.photoRequests.map((r) => [r.incidentId, r.file?.type])).toEqual([
      [1, 'image/jpeg'],
      [1, 'image/jpeg'],
    ])
  })

  it('takes at most five photos', async () => {
    fakeApi.config = { demo_mode: false, vision_enabled: false }
    const { user, sheet } = await openSheet()

    const files = ['1', '2', '3', '4', '5', '6'].map((n) => photo(`${n}.jpg`))
    await user.upload(within(sheet).getByLabelText('Add photos'), files)

    expect(within(sheet).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(5)
    expect(within(sheet).queryByLabelText('Add photos')).not.toBeInTheDocument()
  })

  it('says photos go to the AI provider when vision is on', async () => {
    fakeApi.config = { demo_mode: false, vision_enabled: true }
    const { sheet } = await openSheet()
    expect(
      await within(sheet).findByText('Photos are sent to the AI provider.'),
    ).toBeInTheDocument()
  })
})

describe('the first AI turn waits for the uploads', () => {
  it('asks only once every upload has settled', async () => {
    const release = holdUploads()
    const { user, sheet } = await openSheet()
    await user.click(within(sheet).getByRole('button', { name: 'Flat front tyre' }))
    await user.click(within(sheet).getByRole('button', { name: 'Deep pothole in the road' }))
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    await waitFor(() => {
      expect(fakeApi.photoRequests).toHaveLength(2)
    })
    expect(within(await resultPanel()).getAllByText('Uploading…')).toHaveLength(2)
    // The panel already waits, but has not asked yet.
    expect(within(aiPanel()).getByText('Working out the next steps for you…')).toBeInTheDocument()
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(fakeApi.turnRequests).toEqual([])

    release()

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(1)
    expect(within(photosPanel()).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(2)
  })

  it('still asks when an upload fails, and shows why it failed', async () => {
    fakeApi.config = { demo_mode: false, vision_enabled: false }
    fakeApi.photoScript = [{ status: 415, reason: 'unsupported_media_type' }, 'ok']
    const { user, sheet } = await openSheet()
    await user.upload(within(sheet).getByLabelText('Add photos'), [photo('a.jpg'), photo('b.jpg')])
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))
    await resultPanel()

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(1)
    const failed = within(photosPanel()).getByRole('alert')
    expect(failed).toHaveTextContent(
      'A photo could not be added. That file is not a photo we can use. Send a JPEG, PNG or WebP.',
    )
    // Retrying the same file can't help.
    expect(within(failed).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    await user.click(within(failed).getByRole('button', { name: 'Dismiss' }))
    expect(within(photosPanel()).queryByRole('alert')).not.toBeInTheDocument()
    expect(within(photosPanel()).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(1)
  })
})

describe('photos on the incident', () => {
  it('adds a photo later and removes photos one by one', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)

    const panel = await screen.findByRole('region', { name: 'Photos' })
    expect(within(panel).getByText('No photos yet. Add some to document the damage.'))
    await user.click(await within(panel).findByRole('button', { name: 'Deep pothole in the road' }))
    await user.click(within(panel).getByRole('button', { name: 'Flat front tyre' }))
    await waitFor(() => {
      expect(within(panel).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(2)
    })
    expect(fakeApi.photoRequests.map((r) => r.sampleId)).toEqual(['pothole', 'flat_tyre'])

    await user.click(within(panel).getByRole('button', { name: 'Remove photo 1' }))

    await waitFor(() => {
      expect(within(panel).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(1)
    })
    expect(fakeApi.incidents[0]?.photos.map((p) => p.id)).toEqual([2])
    // Opening an incident later never asks the assistant on its own.
    expect(fakeApi.turnRequests).toEqual([])
  })

  it('hides "add" once the incident has five photos', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)
    const panel = await screen.findByRole('region', { name: 'Photos' })
    for (let i = 0; i < 5; i++)
      await user.click(await within(panel).findByRole('button', { name: 'Flat front tyre' }))

    expect(
      await within(panel).findByText('That is the most photos one incident can have.'),
    ).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: 'Flat front tyre' })).not.toBeInTheDocument()
    expect(within(panel).getByText('5 of 5')).toBeInTheDocument()
  })

  it('a failed upload can be tried again when the connection was the problem', async () => {
    fakeApi.photoScript = [{ status: 503, reason: 'database_unavailable' }]
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)
    const panel = await screen.findByRole('region', { name: 'Photos' })
    await user.click(await within(panel).findByRole('button', { name: 'Flat front tyre' }))

    const failed = await within(panel).findByRole('alert')
    await user.click(within(failed).getByRole('button', { name: 'Try again' }))

    await waitFor(() => {
      expect(within(panel).getAllByRole('img', { name: /^Photo \d$/ })).toHaveLength(1)
    })
    expect(within(panel).queryByRole('alert')).not.toBeInTheDocument()
    expect(fakeApi.photoRequests).toHaveLength(2)
  })
})
