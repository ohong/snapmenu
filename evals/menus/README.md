# Real SF menu evaluation

50 distinct San Francisco restaurants. Five Terra agents collected original restaurant PDF/SVG files and genuine screenshots of text-only menu regions. These are restaurant snapshots, not menus generated for tests. Historical, seasonal, group, and sample menus are marked in each source manifest. Availability and prices are not established as current.

`cases.json` records each source manifest, normalized input hashes, and 3–5 manually transcribed dish checks. The fixed split contains 40 development cases and 10 holdout cases. Do not tune prompts on the holdout results.

`inputs/` contains JPEG pages at a maximum of 1800 pixels, matching the phone upload path. `sources/` preserves originals and provenance. Only manifest-selected menu pages become evaluation inputs; event-packet covers and other unselected pages stay out of extraction. Some screenshots show only a menu section. Each source manifest identifies the original page or captured section. Screenshots are not recreated from scraped text.

## Validate without model calls

```sh
.venv/bin/python evals/menus/prepare.py
```

Checks 50 unique restaurants, source hashes, input preparation, and minimum anchor count. It renders PDF/SVG sources but does not call a model. The source collectors visually checked the saved regions for dish photographs. Hash validation does not independently prove visual fidelity.

## Run a small paid extraction evaluation

Start the real Worker with a valid provider key in `.dev.vars`. Then:

```sh
.venv/bin/python evals/menus/run.py --url http://127.0.0.1:8787 --limit 5 --allow-paid
```

For the entire dataset, use `--split all --limit 50`. First set `HOURLY_SCAN_LIMIT=60` in your local `.dev.vars`; the default ten-scan browser cap otherwise stops the run. Keep the normal production cap unchanged. The default five-case run limits cost. This runner requests extraction only. It does not generate dish pictures unless `--images` is supplied. It stops on rate limits or unavailable credentials and saves results after every case.

The report records HTTP outcome, partial dish-name recall, exact printed-price checks where labels separate prices, upload size, server timing, and elapsed time. The normalizer separates printed price suffixes from dish names. Review anchors against the original page before treating a miss as a model failure. Compare providers with fresh local data and identical inputs. Cached results lack `Server-Timing`; exclude them from latency comparisons.

These anchors do not measure complete-menu recall, invented dishes, translation quality, or image fidelity. Before release, inspect five complete outputs from each provider against their source pages. Review omitted sections, invented ingredients, grouping, prices, and translations. For image quality, generate one dish from each of five varied cuisines and score whether the main ingredient, preparation, and serving style match the printed description. Pictures cannot establish the restaurant's actual plating.

Restaurant content remains the property of its owners. Keep source attribution and use these snapshots for evaluation. The app never serves this corpus to diners.

## Optional image review

Add `--images` to generate one picture from each of the first five successful menus. This adds up to five paid image requests. The report saves private local WebP files under `test-results/menu-eval-images/` and a short rubric with blank human-review fields. Compare each picture with its printed source description. Mark ingredient/preparation matches, plausible serving style, and unsupported additions. The actual restaurant plating remains unknown. Image polling stops after three minutes without resubmitting uncertain work.
