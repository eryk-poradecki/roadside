# Desktop Incident and Report (#114)

Chrome captures after the Impeccable critique pass, using test-fixture incident,
vehicle, advice and report data (not a real driver's record). Viewport height: 1100px.
Map tiles are OpenStreetMap; nearby places use existing test fixtures. Reduced motion
was enabled and fonts and map tiles settled before capture.

| Width | Incident | Report |
| --- | --- | --- |
| 1280 | [Incident](incident-1280.png) | [Report](report-1280.png) |
| 1440 | [Incident](incident-1440.png) | [Report](report-1440.png) |
| 1920 | [Incident](incident-1920.png) | [Report](report-1920.png) |
| 1023 | [Incident](incident-1023.png) | [Report](report-1023.png) |

At 1023px these capture the mobile shell's scroll viewport; content below the fold remains
available by scrolling. All widths had no document overflow. Desktop textarea computed
styles: cursor `text`, user-select `auto`, touch-action `auto`; select-all and double-click
selection verified in Chrome. Desktop is two columns; 1023px is stacked with the mobile dock.

Critique found and fixed a textarea height cascade conflict, a clipped desktop filter,
and unsettled screenshot content. A minor wide-screen gap is retained for text measure.
