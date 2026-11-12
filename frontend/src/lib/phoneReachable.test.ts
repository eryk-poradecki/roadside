import { phoneReachable } from './phoneReachable'

describe('phoneReachable', () => {
  it.each([
    'roadside.example.com',
    'app.fly.dev',
    '8.8.8.8',
    '172.32.0.1',
    '100.64.0.1',
    '[2001:db8::1]',
  ])('is true for the public host %s', (host) => {
    expect(phoneReachable(host)).toBe(true)
  })

  it.each([
    'localhost',
    'app.localhost',
    'printer.local',
    '127.0.0.1',
    '0.0.0.0',
    '10.1.2.3',
    '172.16.0.1',
    '172.31.255.255',
    '192.168.1.20',
    '169.254.10.1',
    '[::1]',
    '[fd12:3456::1]',
    '[fe80::1]',
    '[::ffff:7f00:1]',
    '[::ffff:c0a8:114]',
    'devbox',
    'nas.lan',
    'api.internal',
    'router.home.arpa',
    'host.docker.internal',
    'box.localdomain',
    '',
  ])('is false for %s, which a phone could not open', (host) => {
    expect(phoneReachable(host)).toBe(false)
  })
})
