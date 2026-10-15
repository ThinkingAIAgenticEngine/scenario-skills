# Benchmark Thresholds

Thresholds used by `scripts/analyze_effectiveness.py` (`BENCHMARKS`) and quoted
in the report. They are deliberately coarse: a benchmark exists to point at the
one stage worth investigating, not to grade the campaign.

## Rate benchmarks

| Rate | Threshold | Comparison | Alert | Message |
|---|---|:---:|:---:|---|
| dispatch success (`trigger / actualTrigger`) | 0.90 | below | red | channel configuration warning |
| click-through (`click / view`) | 0.03 | below | orange | content / timing warning |
| unsubscribe | 0.02 | above | orange | frequency warning |

## How a bleed point is chosen

The stage with the largest absolute drop is **never** used, because the
impression-to-click step always loses 95%+ of users (CTR is naturally 3-5%). That
is a property of funnels, not a finding about the campaign.

Instead, for every rate below its benchmark:

```
recoverable = (threshold - actual) * denominator
```

The stage with the largest `recoverable` count becomes the bleed point. If every
rate is at or above benchmark, **no** bleed point is reported - a campaign
without problems should not be given a fabricated one.

Stages downstream of a data break are excluded from the comparison entirely,
because their values are missing rather than low.

## Channel-specific CTR reference points

Used only as orientation when the configured benchmark feels wrong for the
customer's channel. Adjust through `references/benchmark_thresholds.md` rather
than editing the script default silently.

| Channel | Typical CTR | Note |
|---|---|---|
| push notification | 3-8% | the 0.03 default is the conservative floor |
| in-app message | 8-15% | higher because the user is already in the product |
| SMS | 2-6% | heavily dependent on regional regulation |
| EDM | 1-3% | deliverability dominates the outcome |
| popup | 5-12% | sensitive to trigger timing |

## Minimum sample sizes

| Condition | Threshold | Consequence |
|---|---|---|
| window length | >= 3 days | fewer observations give an unstable rate |
| audience size | >= 1000 users | below this a rate difference is not attributable |
| experiment per group | >= 500 users | below this, significance is not meaningful |

Below these levels the analysis still runs, but the report must not present a
conclusion as decision-grade.

## Sandbox calibration notes

Observed on the reference project (id 61) and available for sanity-checking a
new project's numbers:

| Task | plan | trigger | dispatch success |
|---|---|---|---|
| `0822` | 13339 | 10676 | 80.0% - below benchmark, correctly flagged |
| `0006` | 9463 | - | - |
| `0597` | 4683 | - | - |

A dispatch success rate far below 90% is usually a real channel problem. In
sandbox projects it can also mean the delivery receipt was never configured,
which is the same thing the recommendation asks the customer to check.
