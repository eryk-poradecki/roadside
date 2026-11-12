/** IPv4 ranges a phone on another network can't open: loopback, private, link-local, "this host". */
const LOCAL_V4 = [
  /^127\./,
  /^10\./,
  /^192\.168\./,
  /^169\.254\./,
  /^172\.(1[6-9]|2\d|3[01])\./,
  /^0\./,
]

/** Name suffixes that only resolve on a local network. */
const LOCAL_SUFFIXES = ['.localhost', '.local', '.lan', '.internal', '.home.arpa', '.localdomain']

/**
 * Whether a phone scanning a QR code could open this hostname (`location.hostname`, so IPv6
 * comes in brackets). False for localhost, single-label and local-network names, and
 * loopback, private or link-local addresses (ADR 0012: the desktop Start screen then shows
 * no QR code). When unsure, it says no: a missing QR code costs less than a dead one.
 */
export function phoneReachable(hostname: string): boolean {
  const host = hostname.toLowerCase()
  if (!host) return false
  if (host.startsWith('[')) {
    const v6 = host.slice(1, -1)
    // Loopback, unspecified, IPv4-mapped (::ffff:…, the IPv4 rules can't see inside), unique
    // local (fc00::/7) and link-local (fe80::/10).
    return !(
      v6 === '::1' ||
      v6 === '::' ||
      v6.startsWith('::ffff:') ||
      /^f[cd]/.test(v6) ||
      /^fe[89ab]/.test(v6)
    )
  }
  // `localhost` and intranet names such as `devbox` have no dot.
  if (!host.includes('.')) return false
  if (LOCAL_SUFFIXES.some((suffix) => host.endsWith(suffix))) return false
  return !LOCAL_V4.some((range) => range.test(host))
}
