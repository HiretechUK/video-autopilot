# Imagine You: series bible (read by the script writer every time)

## The show
Second-person survival stories. Every episode drops YOU into one scenario and walks through what
happens, day by day, with hard survival rules along the way. It ends on a real A/B choice that viewers
answer in the comments. Tone: tense, smart, a little eerie, never gory. Facts in the rules must be true
(real survival guidance, real history).

## Format (YouTube Short, 50-60 seconds spoken; rule book: autopilot/RULEBOOK_imagine_you.md)
The top channels in this style (2D cartoon characters in 3D worlds) were measured: fast steady narration
(~3.7 words a second, almost no pauses), the hook is the first sentence, every sentence is shown literally,
and the video ends on its last word. Write to that.
- 8-12 scenes. Each scene = one `narration` of 1-3 short sentences (10-30 words). 160-210 words in total.
- Scene 1 = THE HOOK, a paradox or deadly fact stated as fact, in one breath, starting "Imagine you...":
  "Imagine you wake up and the whole city is dark, and the thing that kills most people isn't the cold."
  No setup, no "in this video", no greeting.
- Setting in 1-2 lines with concrete detail (time, place, a number).
- Escalation in 3-5 beats, each a little worse. Time jumps go in the HUD ("DAY 2 · 10:15 AM").
- Two RULES (rule one, rule two): real survival guidance, and each rule must be explained by its real mechanism
  after the pivot "You see," with an everyday comparison ("You see, a generator in a garage is like
  running your car in a closed room: the gas has no smell, so you never know").
- One twist near the end that recolours everything before it.
- Final scene: the choice, short. Narration asks the question, then "Comment A or B." and stops there
  (no "follow", no "find out"). It must have `choice` and `hold_after: 2.0`.
- Title (YouTube): a curiosity gap about a hidden rule or mechanism, max 70 chars, e.g.
  "Why You Should Fill Your Bathtub the Second the Power Dies", "The Mistake That Kills People in Blackouts".
  The narration still opens with "Imagine you...".

## How it should sound (the narrator reads each scene in one natural take)
- Write to be told out loud: short sentences, concrete detail, present tense, "you".
- Use these beats, which the engine turns into real pauses:
  - Question then answer: "Your phone? No signal." (automatic pause after the question)
  - `[pause]` before the turn in a build-up: "No traffic. No sirens. [pause] Your phone? No signal."
  - "..." inside a line for a held breath: "One window... lit up."
- Use `[pause]` at most once per episode (the reference narrators almost never pause). Never at the start or end of a narration.
- No emojis, no hashtags, no stage directions, no sound effects in narration.
- Spell numbers the way they are said ("three days", "tenth floor").

## Moods (whole-scene delivery): calm, tense, whisper, urgent, reveal, warm

## Visual vocabulary (use ONLY these)
- bg: city_night, island, island_night, bunker, forest_night, desert, snow, supermarket, amsterdam_1637
- pose: stand, walk, phone, point, shock, think, sit, crouch, wave, run, drink, lookout, kneel, reach,
  carry, signal (both arms waving overhead), build (working with hands), shiver, cower
- poses: the character must DO things. Give most scenes 2-3 actions in order, acted out across the
  scene, matching the narration (e.g. ["kneel", "drink", "lookout"] for finding rain water).
  "pose" = the first action. Use move_to in some scenes so the character travels.
- props (optional list): car, crate, radio, fire (one fire), fire_triangle (three fires in a triangle),
  ship (light on the horizon, best on island_night), leaf_water, tulip_stall
- What is said must match what is shown: if the narration says three fires, use fire_triangle;
  night scenes use a night background.
- fx (optional): shake, flash, rain, red, dark (city_night only: the city's lights switch off during the scene;
  use when the power fails), window (city_night only: the city is black except one glowing window; use for a
  sign that someone else is out there)
- x: 0.2-0.8 horizontal position; move_to: makes the character walk to that x during the scene
- cam: {"z0": start zoom, "z1": end zoom}, 1.0-1.25
- hud: 2-3 short ALL-CAPS lines; first line is time ("DAY 3 · 06:10 AM"), second starts with "● ",
  third is a stat that matters to this story. Set it on scene 1 and whenever time jumps.
- rule: {"n": 1, "text": "MAX 14 CHARS", "sub": "MAX 18 CHARS"}
- highlight: 1-2 words from that scene's narration to colour yellow
- costume: "cap" for survival episodes (the red-cap YOU)

## Scenario rules
- One clear scenario per episode, different from recent episodes (see the list provided).
- Prefer scenarios people search and argue about: last person on Earth, stranded island, nuclear
  alert, zombie outbreak, lost at sea, avalanche, blackout for a month, trapped in a mall, desert
  crash, alone in space station, frozen in 1900 London, etc. Pick backgrounds that fit.
- The two choice options must both be defensible so the comments argue.

## Picture (v3: 2D characters in 3D sets) — what the writer controls
- Every sentence must be SHOWABLE: pick bg, poses and props that act out exactly what is said.
- Change place (bg) at most 3 times; each change is a flash transition, so use it for time jumps.
- Give most scenes 2-3 poses so the character acts on the words; use move_to so the camera has something to follow.
