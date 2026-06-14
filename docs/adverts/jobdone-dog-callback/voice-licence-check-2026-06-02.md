# JobDone Voice Licence Check

Checked: 2026-06-02

## Short Answer

The regional Voice Library candidates appear usable for commercial advert
experiments if the audio is generated during an active paid ElevenLabs
subscription, using non-beta Text to Speech, and the output complies with
ElevenLabs Terms of Service and Prohibited Use Policy.

Do not use output generated on the free plan for commercial work.

Do not market any app voice as Alexa, Siri, Google Assistant, or any other
branded assistant. Use a generic assistant voice only.

## Official Rules Checked

ElevenLabs Help Center says:

- free plan output does not include a commercial licence and cannot be used for
  commercial purposes
- paid plans include a commercial licence, provided the generation is not using
  Beta Services and the user has the necessary IP rights
- content generated during a paid subscription can be used commercially and
  indefinitely

Official source:
`https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform`

ElevenLabs Voice Library docs say:

- Voice Library voices are community-shared voices
- only Professional Voice Clones can be shared publicly in the Voice Library
- Voice Library voices are not available through the API to free-tier users
- voices can be used directly without saving them to My Voices

Official sources:

- `https://elevenlabs.io/docs/eleven-creative/voices/voice-library`
- `https://elevenlabs.io/docs/overview/capabilities/voices`

ElevenLabs Voice Library Addendum says the Voice Library service makes
ElevenLabs voice models and user voice models available through the service.

Official source:
`https://elevenlabs.io/vla`

## Account Check

The current local API key cannot verify the subscription tier because it lacks
`user_read`.

Observed API response:

```text
missing_permissions: user_read
```

Practical rule: before publishing any advert, verify in the ElevenLabs account
UI that the account is on a paid plan and that the relevant generated assets
were created during that paid plan.

## Candidate Voice Metadata

The v2 regional candidates were queried through:

```text
GET https://api.elevenlabs.io/v1/shared-voices
```

No selected shared voice was returned as `category: famous`.

| Profile | Category | Accent | Notice Period | Live Moderation |
| --- | --- | --- | --- | --- |
| `yorkshire_david` | professional | yorkshire | 730 days | false |
| `yorkshire_paul` | professional | yorkshire | 730 days | false |
| `yorkshire_noah` | professional | british/Yorkshire description | 90 days | false |
| `geordie_andy` | professional | british/Geordie description | 180 days | false |
| `northern_mike` | professional | british/Northern description | none returned | false |
| `scottish_chris` | professional | scottish | 180 days | false |
| `scouse_husky` | professional | scouse | 730 days | false |
| `irish_stephen` | professional | irish | 365 days | false |
| `app_maya` | professional | british | 730 days | false |
| `app_katie` | high_quality | british | 730 days | false |
| `app_clarice` | professional | british | 730 days | false |

`narrator_lily` is an ElevenLabs premade/default-style voice rather than a
shared Voice Library result in this check. It should still be treated under the
same paid-plan commercial-use rule.

## Risk Notes

- Voice Library availability can change. Prefer voices with a long notice period
  for anything that needs repeatable future edits.
- The licence is tied to the ElevenLabs account/plan and Terms, not to a generic
  Creative Commons-style file licence.
- Keep metadata for each generated asset: voice ID, voice name, generation time,
  model, settings, and source text.
- For public adverts, avoid claims that imply endorsement by the voice actor or
  by ElevenLabs.
