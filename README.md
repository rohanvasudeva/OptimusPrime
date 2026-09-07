# OptimusPrime

## Streaming chat

`POST /chat/stream` accepts the same body as `POST /chat` and returns a
`text/event-stream` response. It emits `token` events containing
`{"content": "..."}`, then a `done` event after the completed assistant
message is stored. Provider errors, timeouts, rate limits, and empty replies
are emitted as an `error` event with a safe `message` and `status_code`.
