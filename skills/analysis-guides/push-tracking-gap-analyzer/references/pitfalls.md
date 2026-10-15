# Troubleshooting coverage and output

| Symptom | Likely cause | Correction |
|---|---|---|
| Later source events appear absent | Only the first API page was read | Use a complete Excel export or exhaust pagination; reconcile counts |
| A `.base` file has columns but no records | Schema export mistaken for data | Obtain a workbook containing actual rows |
| D/E values disappear | Rectangular C:E merge | Merge each column independently |
| A different event tag disappears | A repeated tag was merged across intervening tags | Merge adjacent runs only |
| Receipt property descriptions disappear | Entire I span was merged | Keep distinct descriptions unmerged |
| Header or first event is merged incorrectly | An annotation row shifted coordinates after merge generation | Generate for header row 2 and import at A2 without inserting another row |
| Old rows remain below a short replacement | CSV import overwrote only new rows | Clear the confirmed previous managed area before import |
| Property names shifted into E | A continuation row had four empty fields | Generate CSV with five empty A-E cells and verify nine columns |
| A text value is evaluated as a formula | Untrusted text began with `=` before CSV import | Use the supplied generator, which prefixes formula-like text with an apostrophe |
| Styling or merging uses an inverted range | The supplement contains no event/property additions | Treat `data_rows: null` as header-only output and skip data-area operations |
| Types differ for the same property | A synonym was substituted or only the first occurrence checked | Inspect all occurrences; preserve exact source display/type |
| A common property was added again | Common properties or semantic equivalents were not searched | Remove redundant additions and retain coverage evidence |
| An import event was proposed unnecessarily | Existing creation event source enum already covers imports | Check value domains before creating events |
| No-addition strategies vanish from the report | Only CSV additions were counted | Keep a separate complete strategy matrix and compare ID sets |
| CLI rejects an input file | File lies outside its working directory | Put files beneath the task workspace and use relative file arguments |
| Border style is rejected | An unsupported `all` key was used | Specify top/bottom/left/right independently |
| User properties contain the phase label as a name | Columns were read by fixed positions | Match property columns by their header labels |

A proxy event may provide partial evidence without proving full coverage. Mark the limitation. Do not invent source names based on familiar products, and do not substitute unsupported property types.

After any partial Feishu write, read the affected range before retrying. Distinguish local export completion, successful remote write, and verified readback in the final report.
