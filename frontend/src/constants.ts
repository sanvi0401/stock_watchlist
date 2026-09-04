export const TIMEZONES = [
  'Asia/Kolkata',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Sydney',
  'UTC',
]

export const SENSITIVITIES = [
  { id: 'conservative', title: 'Conservative', body: 'Fewer alerts. Only moves far outside this name’s usual range rank HIGH.' },
  { id: 'balanced', title: 'Balanced', body: 'Default. HIGH at 80+, MEANINGFUL at 60+, NOTABLE at 30+.' },
  { id: 'sensitive', title: 'Sensitive', body: 'More alerts. Smaller moves count when you check often.' },
]

export const LOOKBACKS = [
  { id: 'since_last_check', title: 'Since last check', body: 'Compare to the price you saw on your previous visit. The core of this product.' },
  { id: 'previous_close', title: 'Previous close', body: 'Compare to the last official close instead of your visit.' },
  { id: 'five_day', title: 'Five sessions', body: 'Compare to the close five trading days ago.' },
]
