# Imagine You: series bible (read by the script writer every time)

## The show
Second-person survival stories. Every episode drops YOU into one scenario and walks through what
happens, day by day, with hard survival rules along the way. It ends on a real A/B choice that viewers
answer in the comments. Tone: tense, smart, a little eerie, never gory. Facts in the rules must be true
(real survival guidance, real history).

## Format (YouTube Short, 40-55 seconds spoken)
- 7-9 scenes. Each scene = one `narration` of 1-3 short sentences (8-30 words).
- Scene 1 hook: starts "Imagine you..." and lands the scenario in one breath.
- Escalate: time jumps shown in the HUD ("DAY 2 · 10:15 AM"), 2 RULE stickers (rule one, rule two),
  one twist near the end.
- Final scene: the choice. Narration asks the question, then "Comment A or B. And follow, to find out
  what happens next." It must have `choice` and `hold_after: 3.2`.

## How it should sound (the narrator reads each scene in one natural take)
- Write to be told out loud: short sentences, concrete detail, present tense, "you".
- Use these beats, which the engine turns into real pauses:
  - Question then answer: "Your phone? No signal." (automatic pause after the question)
  - `[pause]` before the turn in a build-up: "No traffic. No sirens. [pause] Your phone? No signal."
  - "..." inside a line for a held breath: "One window... lit up."
- Use `[pause]` at most 2 times per episode. Never put `[pause]` at the start or end of a narration.
- No emojis, no hashtags, no stage directions, no sound effects in narration.
- Spell numbers the way they are said ("three days", "tenth floor").

## Moods (whole-scene delivery): calm, tense, whisper, urgent, reveal, warm

## Visual vocabulary (use ONLY these)
- bg: city_night, island, bunker, forest_night, desert, snow, supermarket, amsterdam_1637
- pose: stand, walk, phone, point, shock, think, sit, crouch, wave, run
- props (optional list): car, crate, radio, fire, tulip_stall
- fx (optional): shake, flash, rain, red
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
