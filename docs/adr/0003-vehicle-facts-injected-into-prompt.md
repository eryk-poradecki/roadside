# Vehicle facts are injected into the prompt, not fetched by a tool

The backend loads the incident's vehicle and puts a short "Vehicle" fact block into the user message. The model has no `get_vehicle_profile` tool. Every answer needs the vehicle context, so the model should never have to choose to fetch it. Local Ollama models can't be forced to call a tool (no `tool_choice` on `/v1`, see [research #6](https://github.com/eryk-poradecki/roadside/issues/6)), so a small model could skip the call and answer about the wrong car. A tool call also costs an extra model round, which is slow on an 8 GB GPU. Tools are kept for decisions the model actually makes, like which nearby category to look up.

## Considered Options

- **Tool `get_vehicle_profile`** (the kickoff plan). Rejected: the model can't be forced to call it, and it costs an extra round for context that is always needed.
- **Both injected and as a tool.** Rejected: redundant, and two paths to the same facts can disagree.

## Consequences

- **Unknown is not "none".** Every vehicle attribute is nullable, and null means "unknown, assume nothing". It is never treated as "none". `spare_wheel` is `full_size | space_saver | repair_kit | none`; `wheel_locks` is `true | false`, with a free-text `lock_key_location` only when it is true. The model says "you have no spare" only for `none`.
- **Fuel type and transmission change the advice.** `fuel_type` is `petrol | diesel | lpg | hybrid | plug_in_hybrid | electric`. `transmission` is `manual | automatic`; the form hides it for `electric` and stores null. These rules live in the prompt:
  - push start only for a manual that is not electric or hybrid;
  - automatics and EVs get a "tell the tow company, flatbed preferred" line;
  - diesel gets the priming note after running dry;
  - for an LPG car that ran dry or won't start, check whether the system has switched to petrol on its own (the indicator and a beep). This hint is added to the user message only when `fuel_type` is `lpg`, so a petrol car or an unknown fuel type never hears about LPG (#90);
  - flat battery always means the 12 V battery.
- **Fuel type is one choice, with known simplifications (#107).** LPG installations are fitted to petrol (spark-ignition) engines, so `lpg` means petrol + LPG. The form labels it "Petrol + LPG" ("Benzyna + LPG"), and the fact block tells the model "petrol engine with an LPG installation". The stored value, including in the snapshot, stays `lpg`: the wording is applied when the block is rendered, the same way every time. Two rarer cases fold into another option:
  - a diesel dual-fuel car (diesel + LPG) is entered as `diesel`, since diesel behaviour (priming after running dry) dominates;
  - a petrol hybrid with an LPG conversion is entered as `hybrid`: the push-start and towing advice matter more, and the LPG system switches to petrol on its own when the gas runs out (#90). The form says so in a one-line hint under the field.
- **Out of fuel means out of charge for an EV.** There is still one problem type, `out_of_fuel`. For an electric vehicle, its label reads "Out of charge" and the nearby category is charging stations (`amenity=charging_station`) instead of fuel stations. The Start tile label follows the default vehicle. The vehicle chosen for the incident decides everything from the sheet on: the sheet header, the Result screen and the nearby category.
- **Some fields never reach the model.** These are `registration`, `assistance_phone` and `policy_number`. The frontend renders the "Call <insurer>" button and the policy number from the Vehicle, so a phone number can never be hallucinated. The model sees "has assistance, insurer <name>" only when a phone is set; a name without a phone counts as no assistance. The model does see `name`, `make_model`, `year` and `tyre_size`.
- **The snapshot is the fact block.** The AI answer stores exactly the vehicle block sent to the model, plus `name`, and "Answered for …" is rendered from it. What the model saw and what the screen shows are the same object. A retry after a failure builds the block from the vehicle's current state (a deleted vehicle means no vehicle). Switching the incident's vehicle after the answer exists never changes or regenerates the answer.
- **No vehicle means assume nothing.** The block says no vehicle details were given, so the model gives general options. The Result screen invites the driver to add a car only when they have no vehicles at all. A driver who has vehicles and picked none did so on purpose.
- **Vehicle-conditional steps come from prompt rules over the fact block**, not tagged steps filtered by the backend. The safety checklist stays static and vehicle-agnostic.
