const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

if (!configuredApiBaseUrl) {
  throw new Error(
    'VITE_API_BASE_URL is missing. Check your frontend environment configuration.',
  )
}

const parsedApiBaseUrl = new URL(configuredApiBaseUrl)

if (!['http:', 'https:'].includes(parsedApiBaseUrl.protocol)) {
  throw new Error('VITE_API_BASE_URL must use HTTP or HTTPS.')
}

export const API_BASE_URL = parsedApiBaseUrl.toString().replace(/\/+$/, '')
