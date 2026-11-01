# Imagine You rule book (1 Nov 2026)

Why Rick's Clips and the channels like it win, and exactly how Imagine You copies the *method* (never the content).

## The evidence
- **Rick's Clips, last 30 Shorts.**
  - The 24 newest are 2D cartoon characters in colourful 3D sets: 0.1M-30M views, median about 6.5M.
  - The 6 older ones are reposted comics over Minecraft parkour: 45k-381k views, median about 0.07M.
  - Same channel, same audience, about 90x the views. The format is the difference.
- **Measured detail** comes from the open study in github.com/mromidev/claude-animated-shorts: 20 Shorts of the same style, 32,337 frames measured at 30 fps.
  - Rick's own video files couldn't be downloaded (YouTube blocks cloud servers).
  - Our Rick's analysis therefore uses all 30 cover frames and YouTube's auto frames.

## 1. Story rules (writer + bible_imagine_you.md)
1. **Hook in sentence one.** A paradox or deadly fact stated as fact, no setup ("Imagine you... and the thing that kills most people isn't the cold."). The voice starts on frame 1.
2. **Curiosity-gap titles.** Their titles name a hidden mechanism or loophole: "Why Sailors Carried Storm Oil", "The Burglar Who Only Moved Furniture". Ours: "Why You Should Fill Your Bathtub the Second the Power Dies".
3. **Fast, steady voice.** About 3.7 words a second, almost no pauses, 50-60 s (160-210 words).
4. **Escalate in 3-5 beats.** Each beat is a little worse than the last.
5. **Explain the mechanism.** Use the pivot "You see," and an everyday comparison. The rules must be true and explained, not just stated.
6. **Twist, then stop.** One twist near the end, then the A/B question. End on "Comment A or B." with no "follow" call (the reference videos end on their last word).
7. **Show everything.** Every sentence is shown literally on screen. Never describe what the viewer already sees.

## 2. Picture rules (engine/renderer_v3.html)
8. **2D characters, 3D world.** Flat cartoon characters in a detailed, saturated 3D set. Never in front of empty space: put a lit shopfront, shelves or trees right behind the character.
9. **Character build.**
   - Big round bean head (about 30% of height), bean torso, thin ink stick limbs and ink-dot hands.
   - Plum ink outline (#241726).
   - Our brand stays: the red cap and orange survival vest.
10. **Characters are lit by the scene.** They take the scene's light (warm lamps, fire, moonlight) and cast a real shadow.
11. **Ink lines on the 3D world.** About 3 px near-black lines on silhouettes and depth jumps.
12. **Colour.** Bright, saturated colour with lifted blacks and a soft vignette. Night is blue-violet with warm light pools, never plain black.
13. **Lens blur** on close and medium shots, focused on the character. Wide shots stay sharp.
14. **Camera.**
    - The camera almost never cuts. It glides between framings over about 23 frames (smooth ease in and out).
    - It keeps creeping in about 0.14% per frame, so it is never dead still.
    - No hand-held wobble. Dutch tilts of 4° on tense beats.
15. **Place changes** are a 4-frame white flash, not a cut.
16. **Captions.** One word at a time, white bold with a thin black outline, at about 53% of the height. Key words in yellow.
17. **Little on-screen text.** Only a small day/time chip, the rule card for 2.5 s, and the A/B card at the end. No series badge, no progress bar, no stat lines.
18. **Acting.** The character acts on the words: 2-3 actions per scene, bouncy planted walks, blinks every 0.5-2.3 s.

## 3. Production rules (unchanged)
19. **Free stack.** Kokoro voice, three.js in headless Chromium, ffmpeg. Rendered on GitHub; no paid video generation.
20. **Approval.** Every episode is emailed to Haseeb for approval before posting, and is then guarded against duplicates and missed platforms (see the CEO agent).
