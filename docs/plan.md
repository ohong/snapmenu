# Release plan

## Implemented locally

- TypeScript Worker, D1 migration, private R2 storage, and scheduled expiry.
- React/Base UI single-screen upload and paged visual menu.
- Browser image normalization and lazy PDF rendering.
- Muse/OpenAI provider flag with persisted provider-specific task ownership.
- Visible-dish automatic generation, recovery, duplicate claims, and request caps.
- 50 real SF source menus with provenance and a fixed 40/10 evaluation split.

## Required before claiming live readiness

1. Configure an active Meta key, or a working OpenAI key.
2. Run a five-case live extraction check on each enabled provider.
3. Review complete outputs and five diverse generated dish pictures against source descriptions.
4. Measure upload, first text, first image, and complete visible-page latency on a phone network.
5. Provision D1/R2, apply migrations, configure secrets, and deploy the Worker.
6. Exercise deployed ownership, image recovery, deletion, and scheduled expiry.
7. Test an actual iPhone and Android device, including camera selection, browser chrome, landscape, and long translated text.

The repo is not a live deployment. Simulated provider checks do not establish model quality, speed, price, or account access. No Decisions API call is part of the current product.
