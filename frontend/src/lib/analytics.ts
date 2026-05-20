export function trackEvent(eventName: string, properties?: Record<string, unknown>) {
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.log("[analytics]", eventName, properties ?? {});
  }
  // Future: forward to GA4 / Mixpanel / PostHog
}
