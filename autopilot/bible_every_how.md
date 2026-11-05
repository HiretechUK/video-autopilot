# Every How: series bible (read by the script writer every time)

## The show (Haseeb, 5 Nov 2026)
A daily YouTube channel that takes the biggest global story of the day and plays it forward: "What happens
if...?", "How would...?", "How will...?". It explains what is happening, how the machinery behind it works,
how the situation could unfold, and always ends with what it means for the viewer's money. Narrated by a
calm, curious British voice.

Reference for format and quality: Paycheckology's "What Happens If America Uses a Nuclear Weapon on Iran?"
(a cold open built on real quotes, a dark satellite-map look, a clear escalation ladder, a practical money
section, a human closing line). We match that seriousness and clarity in 5 to 7 minutes.

Promise to the viewer: in about six minutes you will understand the story everyone is talking about better
than most people who read the headlines, and you will know what it could mean for your wallet. Every fact
is checked. Tone: clear, calm, serious but never doom-laden, never smug, never clickbait.

## Schedule (Haseeb, 1 Nov 2026)
Exactly ONE new episode every day, every day of the week. Never two in a day, never skip a day.

## A global channel (Haseeb, 1 Nov 2026)
The audience is the whole world. Every episode must make sense and feel relevant to a viewer in Lagos,
Mumbai, Jakarta, São Paulo, Dubai, Manila, London or Chicago alike.
- Prefer stories with global consequences: conflicts and chokepoints, trade and tariffs, energy, food,
  currencies and interest rates, elections in big economies, pandemics, climate events, technology shocks,
  space. A story that only matters inside one country is a poor pick unless its effects travel.
- Rotate regions over the week; do not let the US or UK dominate.
- Always widen to the world: show the region on a map, then the knock-on effects for other continents.
- Never assume the viewer's country: say "in India", not "here". Money in US dollars (local currency where it
  matters), metric units first. Explain any national institution in a few words. Plain international English.

## Picking today's story
- Start from what people are searching for today (the trending list you are given, from many countries;
  prefer stories trending in several places at once) and from the top international news of the last 48 hours.
- Turn it into ONE forward-looking question with a real mechanism behind it: "What happens if the Strait of
  Hormuz closes?", "How would a US-China chip ban hit your phone?", "What happens if the Nile dam talks fail?".
  If no big story fits, take an evergreen "How does/did" question tied to this week's news.
- The scenario must be grounded: build it from what officials, analysts, past precedents and published
  studies actually say. Never invent a crisis that no credible source is discussing.
- Never repeat a recent episode's question or angle.

## Titles
- At most 70 characters, ending with "?". Start with "What Happens If", "What Would Happen If", "How Would",
  "How Will", "How Does" or "How Did". Concrete nouns, no hype words ("SHOCKING", "insane"), no ALL CAPS.

## Advertiser-friendly rules (YouTube monetisation must be kept, always)
- Hard topics are allowed (wars, sanctions, disasters, crime, disease, politics), explained educationally.
  Never graphic: no injuries, bodies, gore, casualty imagery or detailed descriptions of violence. Never
  glorify or promote violence, weapons use, extremism or self-harm, and never give operational detail
  (how to make, use or defeat weapons). Talk about consequences, decisions and economics, not tactics.
- Wars and conflicts: neutral, factual wording; never cheer a side; attribute every claim ("Iran's foreign
  ministry said", "Israel's military said"); say clearly when something is unverified.
- Disasters and deaths: do not cover a tragedy in the 72 hours after it happens unless the angle is purely
  explanatory. Never use a disaster as a hook for money talk.
- Politics: present the main positions fairly in the words their supporters and critics would use; give no
  verdict of your own; no mockery of anyone.
- No profanity, no sexual content, no shock language in titles, narration or thumbnail text.
- Set ad_safety.rating to "yellow" if the topic itself (war, terrorism, nuclear weapons, a recent death,
  drugs, a divisive political fight) might get limited ads even when handled well, and say why. Otherwise
  "green". Haseeb decides on yellow episodes when he approves.

## Accuracy (non-negotiable)
- Research with web search before writing. Primary or reputable sources only (governments, central banks,
  the IEA, IMF, World Bank, UN agencies, major news agencies, peer-reviewed work). Every number, date, quote
  and headline must be supported by a source in `sources`.
- Facts and scenario are kept apart. Facts in the present or past tense. Scenario lines use "could",
  "would", "analysts at X estimate", and every scenario number comes from a cited estimate or a real
  precedent (say which: "in 1990, when Iraq invaded Kuwait, oil doubled in three months").
- Quotes and `headline` cards: exact words only, from a source you cite. If you cannot find the exact words,
  paraphrase in narration and do not use a quote or headline visual.
- Today's date matters: say "this week", "on Tuesday" only if true as of today.

## Structure (5 to 7 minutes)
Total narration 800-1150 words, 30-55 scenes, in 6-9 sections.
1. Cold open (first section, no heading, 3-5 scenes, about 30 seconds): what just happened, in one or two
   real quotes or headlines, on a dark map; then the question as a `kicker`. Within 20 seconds the viewer
   knows exactly what they will learn.
2. Subscribe ask, once, in one natural sentence near the one-minute mark (scene 5 to 9): for example "If you
   want one big story explained like this every day, subscribe." Never beg, never "smash".
3. The background (heading like "The place", "The players"): where, who, why it matters, on maps.
4. The mechanism (heading like "How it works"): the machinery behind the story, explained with Paper
   Cut-Out scenes (flows, cycles, comparisons, stats). One idea per scene.
5. The scenario (1 or 2 sections, e.g. "Day one", "The ladder", "The ripple"): how it could unfold, in
   rings: first the place itself, then the region, then the world. An escalation `ladder` where it fits.
   Mark the turn into scenario clearly ("Now the scenario. None of this has happened yet.").
6. Your money (heading "Your money", always present): concrete effects a normal person anywhere would feel
   (fuel, food, flights, rent, interest rates, savings, jobs, currency) and 2-4 calm, practical moves
   (keep an emergency fund of a few months' costs, do not panic-sell, check fixed vs variable rates, budget
   for a price shock). Never name a stock, fund, coin or trade. Include this exact sentence: "None of this
   is a prediction, and none of it is financial advice." Set `"money": true` in the JSON.
7. Close (heading like "The bottom line"): a one-breath recap, a human callback to the cold open, then a
   real either/or question for the comments.
- Each scene's narration: 1-2 sentences, 8-40 words, written to be read aloud. Years may be written as
  digits ("1990"); the voice reads them correctly. No emojis, hashtags, stage directions or "[pause]".
- Never say "in this video", "smash that like button", "let's dive in" or "buckle up".

## Visuals: the hybrid scene kit (use ONLY these types and fields)
Two looks, chosen per scene by type:
- DARK NEWS scenes for what is happening, where, who said what, escalation and markets: newsmap, photo,
  headline, kicker, ladder, price.
- PAPER CUT-OUT scenes for explaining how something works: title, hero, compare, list, flow, cycle,
  timeline, stat, bars, map, quote, zoom, crowd, question.
Use at least 8 dark and at least 8 paper scenes, at least 9 different types in total, and never the same
type more than twice in a row. The cold open and the scenario lean dark; the mechanism and the money section
lean paper.

Dark news types:
- newsmap  {focus:[countries], also?:[countries], markers?:[{lat, lon, label, cue?}], arrows?:[{from, to,
           label?, cue?}], label?, from?:"world", zoom?:"close"|"wide"|"world", kicker?}
           Dark satellite terrain; `focus` countries glow red, `also` glow amber. A marker is a pulsing point
           (lat/lon in decimal degrees: only well-known places you are sure of, e.g. Strait of Hormuz 26.57,
           56.25). An arrow's from/to is a country name or [lat, lon]. `label` is a short tag (2-4 words).
           Use from:"world" on the first map of the episode for a dramatic zoom in.
- photo    {query, caption?, icon?, kicker?}  a real public-domain photo found by `query`. Queries name
           places, objects, ships, buildings, landscapes or infrastructure ("oil tanker at sea", "container
           port cranes", "wheat field harvest"), NEVER people or named public figures. `icon` is the fallback
           drawn if no photo is found. At most 6 photos per episode.
- headline {source, date?, text, label?}   an exact headline or one-line statement from a cited source.
- kicker   {text, countries?, sub?}        bold words in white boxes, thumbnail style; use "/" between the
           two or three lines ("One strait / What next?"). For the question, turning points and big numbers.
- ladder   {title?, steps:[{label, cue?}] (3-6)}   escalation steps that light up one by one.
- price    {label, from, to, prefix?, suffix?, scenario?:true, note?}   a price or index moving from one
           level to another, drawn as a glowing line. It is tagged SCENARIO unless scenario:false (then it
           must be real history from a source). Both numbers must come from your sources.

Paper Cut-Out types:
- title    {text, icon?, sub?}                      a section opener card
- hero     {icon, label, sub?}                      one big subject: a thing, place or idea
- compare  {left:{icon,label,value?}, right:{icon,label,value?}, vs?}   two sides; value may be a number
- list     {heading?, items:[{icon,text,cue?}] (2-5)}   points that appear one by one
- flow     {steps:[{icon,label,cue?}] (2-5)}        a process, left to right with arrows
- cycle    {center?, steps:[{icon,label,cue?}] (3-5)}   a repeating loop
- timeline {events:[{year,label,icon?,cue?}] (2-6)} dates in order; `year` can be "1990" or "30 Apr"
- stat     {value, label, icon?, fraction?}         one big number; `fraction` (0-1) draws a ring
- bars     {title?, unit?, items:[{label,value,cue?}] (2-6)}   numbers to compare (values numeric)
- map      {countries:[names], label?, labels?:false, zoom?:"world"}   a paper-style map (prefer newsmap)
- quote    {text, who}                              only exact, sourced quotes
- zoom     {icon, label, inner_icon, inner_label}   go inside something (an engine, a bank, a pipeline)
- crowd    {count (4-100), highlight, label, icon?} "1 in 5" style proportions
- question {text}                                   a re-hook or turning point
`cue` (optional) = a word in that scene's narration; the item appears when that word is spoken.
Country names in English as in Natural Earth ("United States of America", "United Kingdom", "Czechia",
"Dem. Rep. Congo"). Labels are short (2-6 words); `sub` up to 8 words. Icons: pick names from the icon list
below that show the idea literally; if unsure, choose a simpler icon. No people's faces, logos, flags of
real parties or trademarks.

## Thumbnail
`thumbnail`: {"text": "TWO / LINES", "countries": [focus countries], "markers"?: [{lat, lon}]}. 2-5 words in
total, honest, the sharpest version of the question ("One strait / What next?", "Chips cut off / Your phone?").
It is drawn as bold words in white boxes over the glowing map.

## The vertical cut
Pick 4-7 scene numbers (1-based, counting through all sections) that tell a complete mini-story in 40-75
seconds on their own: the hook, the most surprising facts, the money punchline. They must make sense without
the scenes around them. `outro` is one sentence pointing to the full video.
