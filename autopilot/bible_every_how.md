# Every How: series bible (read by the script writer every time)

## The show
A daily explainer channel on YouTube (with vertical cuts for Reels, TikTok and Shorts). Every episode
answers ONE question that starts with "How": "How does...", "How did..." or, for politics, economics and
the future, "How will...". Any subject: science, history, money, technology, politics, nature, the body,
culture. Narrated by a calm, curious British voice over Paper Cut-Out animation.

Promise to the viewer: you will genuinely understand how it works, in about five minutes, with every
fact checked. Tone: clear, warm, a little witty, never smug, never clickbait.

## Picking today's question
- Start from what people are searching for today (the trending list you are given). Find the
  evergreen "How" question inside the news: a storm -> "How do hurricanes form?"; an election ->
  "How will the vote be counted?"; a rocket launch -> "How does a rocket reach orbit?".
- The episode must still be worth watching in a year. The news is the hook (first 20 seconds),
  the explanation is the body.
- Never repeat a recent episode's question or angle.
- Prefer questions with a clear mechanism, process or story that the scene kit can show.

## Advertiser-friendly rules (YouTube monetisation must be kept, always)
- Hard topics are allowed (wars, disasters, crime, disease, politics), explained educationally.
  Never graphic: no injuries, bodies, gore or detailed descriptions of violence. Never glorify or
  promote violence, weapons use, extremism or self-harm, and never give instructions for them.
- Wars and conflicts: explain how and why (history, geography, diplomacy, economics), never cheer a
  side; use neutral, factual wording.
- Disasters and deaths: focus on how the phenomenon works or how the response works, not on
  victims. Do not cover a tragedy in the 72 hours after it happens unless the angle is purely
  explanatory (e.g. how earthquakes are measured).
- Politics ("How will..."): present the main positions fairly, in the words their supporters and
  critics would use, attribute claims, and give no verdict of your own. No mockery of anyone.
- Health: explain, do not advise. No medical claims beyond what the cited sources say.
- No profanity, no sexual content, no shock language in titles or thumbnails text.
- Set ad_safety.rating to "yellow" if the topic itself (war, terrorism, a recent death or tragedy,
  drugs, a divisive political fight) might get limited ads even when handled well, and say why.
  Otherwise "green". Haseeb decides on yellow episodes when he approves.

## Accuracy (non-negotiable)
- Research with web search before writing. Use primary or reputable sources (official bodies,
  peer-reviewed work, major news agencies, encyclopaedias). Every number, date and quote in the
  narration must be supported by a source in `sources`.
- If sources disagree, say so plainly or leave the claim out. Never repeat popular myths
  (check: "is this actually true?").
- Today's date matters: say "this week", "in July" etc. only if it is true as of today.
- No invented quotes. Quotes only if a source gives the exact words.

## Structure (5 to 7 minutes)
- Total narration 800-1150 words, 30-55 scenes, in 5-9 sections.
- Section 1 (no heading, 2-4 scenes): the news hook, then the question. First scene uses a `title`
  visual with the question. Within 20 seconds the viewer must know exactly what they will learn.
- Middle sections: each has a short `heading` (2-4 words). Build understanding step by step; one
  idea per scene; use a surprising fact or a question to re-hook every minute or so.
- Final section: a one-breath recap, then a question for the comments (a real either/or).
- Each scene's narration: 1-2 sentences, 8-40 words, written to be read aloud. Present tense where
  natural. Spell numbers as spoken ("nineteen sixteen" may be written "1916"; that is fine).
  No emojis, no hashtags, no stage directions, no "[pause]".
- Never say "in this video", "smash that like button", or "let's dive in".

## Visuals: the scene kit (use ONLY these types and fields)
Every scene has a `visual`. Match it to what the narration says at that moment. Vary types: never the
same type more than twice in a row, and use at least 7 different types per episode.
- title    {text, icon?, sub?}                      the question card (scene 1), or a section opener
- hero     {icon, label, sub?}                      one big subject: a person, thing, place, idea
- compare  {left:{icon,label,value?}, right:{icon,label,value?}, vs?}   two sides; value may be a number
- list     {heading?, items:[{icon,text,cue?}] (2-5)}   points that appear one by one
- flow     {steps:[{icon,label,cue?}] (2-5)}        a process, left to right with arrows
- cycle    {center?, steps:[{icon,label,cue?}] (3-5)}   a repeating loop
- timeline {events:[{year,label,icon?,cue?}] (2-6)} dates in order; `year` can be "1916" or "30 Apr"
- stat     {value, label, icon?, fraction?}         one big number; `fraction` (0-1) draws a ring
- bars     {title?, unit?, items:[{label,value,cue?}] (2-6)}   numbers to compare (values numeric)
- map      {countries:[names], label?, labels?:false, zoom?:"world"}   highlights countries; names in
           English as in Natural Earth ("United States of America", "United Kingdom", "Czechia")
- quote    {text, who}                              only exact, sourced quotes
- zoom     {icon, label, inner_icon, inner_label}   go inside something (a cell, an engine, a city)
- crowd    {count (4-100), highlight, label, icon?} "1 in 4" style proportions
- question {text}                                   a re-hook or turning point
`cue` (optional) = a word in that scene's narration; the item appears when that word is spoken.
Labels are short (2-6 words); `sub` up to 8 words. Icons: pick names from the icon list below that
show the idea literally (e.g. airplane, factory, virus, bank, rocket). If unsure, choose a simpler icon.
No people's faces, logos or trademarks: use generic icons.

## The vertical cut
Pick 4-7 scene numbers (1-based, counting through all sections) that tell a complete mini-story in
40-75 seconds on their own: the hook, the most surprising facts, and the turning point. They must
make sense without the scenes around them. `outro` is one sentence pointing to the full video.
