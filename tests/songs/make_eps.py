"""Writes the Paws & Claws episode song requests (ep02-ep10). Every episode follows one template so shots can be
planned automatically: Intro, Chorus, Verse Rory, Chorus, Verse Ziggy, Chorus, Verse Waffles, Chorus, Verse Pebble,
Bridge, Chorus, Chorus, Outro."""
import json

CAPTION = ("Cheerful children's sing-along song for preschool TV in the style of modern nursery-rhyme channels, warm friendly "
           "lead vocals with a happy group of cartoon animal voices joining on the chorus, call and response, {inst}, "
           "playful animal sound effects, catchy repeating chorus, {mood}, major key, polished modern kids music production, "
           "clear diction, easy for toddlers to sing along")
BRIGHT = "bright ukulele, glockenspiel, hand claps, bouncy bass, light drums"

EPS = {
 "ep02-rainbow-colours": dict(bpm=116, inst=BRIGHT, mood="happy",
  intro=["Hey hey! It's the Paws and Claws Club!", "Let's find the colours! Let's go!"],
  chorus=["Red and yellow, green and blue,", "Colours all around for me and you!", "Look up high and look down low,", "Paws and Claws, let's find a rainbow!"],
  verses=[["Rory found something red, red, red,", "A big red apple on the garden bed!", "Red, red, can you see?", "Point to something red with me!"],
          ["Ziggy found something yellow and bright,", "A yellow sunflower, what a sight!", "Yellow, yellow, can you see?", "Point to something yellow with me!"],
          ["Waffles found something green, green, green,", "The greenest leaf he's ever seen!", "Green, green, can you see?", "Point to something green with me!"],
          ["Pebble found something blue, blue, blue,", "The big blue sky and the ocean too!", "Blue, blue, can you see?", "Point to something blue with me!"]],
  bridge=["Red! Yellow! Green! Blue!", "A rainbow of colours for me and you!", "Red! Yellow! Green! Blue!", "Hooray for the rainbow, woo hoo hoo!"],
  outro="Bye bye, friends! See you next time!"),
 "ep03-counting-fun": dict(bpm=118, inst=BRIGHT, mood="happy, energetic",
  intro=["Hey hey! It's the Paws and Claws Club!", "Get your fingers ready! Let's count!"],
  chorus=["One, two, three, four, five,", "Counting makes us feel alive!", "Six, seven, eight, nine, ten,", "Paws and Claws, let's count again!"],
  verses=[["Rory has one big ball to bounce,", "Bounce it, bounce it, let's all count!", "One! One! Bounce, bounce, bounce,", "Rory's got one ball to bounce!"],
          ["Ziggy has two pink balls of yarn,", "Rolling, rolling round the barn!", "One, two! Roll, roll, roll,", "Ziggy's got two balls to roll!"],
          ["Waffles has three bones to hide,", "Dig, dig, dig, in the garden outside!", "One, two, three! Dig, dig, dig,", "Waffles' bones are hidden deep!"],
          ["Pebble has four fish for tea,", "Splash, splash, splashing in the sea!", "One, two, three, four! Splash, splash, splash,", "Pebble eats them in a flash!"]],
  bridge=["Hold up one finger, now hold up two,", "Three, four, five, now how about you?", "Wiggle all ten, wiggle them high,", "Ten little fingers waving bye bye!"],
  outro="Great counting, friends! See you next time!"),
 "ep04-bath-time": dict(bpm=112, inst="bright ukulele, glockenspiel, bubbly sound effects, hand claps, bouncy bass, light drums", mood="happy, splashy",
  intro=["Hey hey! It's the Paws and Claws Club!", "Uh oh, we're muddy! Bath time!"],
  chorus=["Splish splash, it's bath time,", "Bubbles, bubbles, we feel fine!", "Scrub a dub, rub a dub, one, two, three,", "Squeaky clean for you and me!"],
  verses=[["Rory's mane is full of mud,", "Scrub, scrub, scrub with lots of suds!", "Shampoo bubbles on his head,", "Now Rory's mane is fluffy instead!"],
          ["Ziggy doesn't like the tub,", "But she tries a little scrub!", "Paws in first, one, two, three,", "Ziggy's brave as brave can be!"],
          ["Waffles jumps in with a splash,", "Water everywhere in a flash!", "Shake, shake, shake your fur,", "Waffles is the cleanest pup there were!"],
          ["Pebble loves the water most,", "He floats around just like a boat!", "Flap, flap, swim around,", "Pebble's happiest sploshing round!"]],
  bridge=["Wash your face! Wash, wash, wash!", "Wash your paws! Wash, wash, wash!", "Wash your tummy! Wash, wash, wash!", "Wash your toes! Splish, splash, splosh!"],
  outro="Squeaky clean! Bye bye, friends!"),
 "ep05-brush-your-teeth": dict(bpm=114, inst=BRIGHT, mood="happy",
  intro=["Hey hey! It's the Paws and Claws Club!", "Grab your toothbrush! Let's go!"],
  chorus=["Brush, brush, brush your teeth,", "Up on top and underneath!", "Round and round and side to side,", "Shiny teeth and a smile so wide!"],
  verses=[["Rory has big teeth for a roar,", "Brush them, brush them, brush some more!", "Top teeth, bottom teeth, one, two, three,", "Rory's roar is sparkly clean!"],
          ["Ziggy brushes after tea,", "Tiny teeth as white as can be!", "Swish and spit and rinse it out,", "Ziggy smiles and gives a shout!"],
          ["Waffles brushes, foamy and white,", "Bubbles on his nose, what a sight!", "Brush the front and brush the back,", "Waffles' teeth go clickety clack!"],
          ["Pebble's beak needs a little scrub,", "Tickle, tickle, scrub a dub!", "Up and down and all around,", "Pebble's beak is shiny now!"]],
  bridge=["Brush the top! Brush, brush, brush!", "Brush the bottom! Brush, brush, brush!", "Now swish, swish, swish, and spit it out,", "Show your smile and give a shout!"],
  outro="Sparkly smiles! Bye bye, friends!"),
 "ep06-animal-sounds": dict(bpm=118, inst=BRIGHT + ", farmyard sound effects", mood="happy, silly",
  intro=["Hey hey! It's the Paws and Claws Club!", "Let's make some noise! Let's go!"],
  chorus=["What do the animals say, say, say?", "Let's all make the sounds today!", "Loud sounds, soft sounds, one, two, three,", "Make the animal sounds with me!"],
  verses=[["Rory the lion goes roar, roar, roar,", "A great big roar from the jungle floor!", "Roar like Rory, loud as can be,", "Roar, roar, roar with me!"],
          ["Ziggy the kitten goes meow, meow, meow,", "Soft and gentle, show me how!", "Meow like Ziggy, quiet as can be,", "Meow, meow, meow with me!"],
          ["Waffles the puppy goes woof, woof, woof,", "Woof so loud it shakes the roof!", "Woof like Waffles, happy as can be,", "Woof, woof, woof with me!"],
          ["Pebble the penguin goes squawk, squawk, squawk,", "Squawking as he likes to walk!", "Squawk like Pebble, silly as can be,", "Squawk, squawk, squawk with me!"]],
  bridge=["Roar! Meow! Woof! Squawk!", "Now let's do them all and walk!", "Roar! Meow! Woof! Squawk!", "The Paws and Claws Club loves to talk!"],
  outro="What a noisy club! Bye bye, friends!"),
 "ep07-wiggle-your-body": dict(bpm=122, inst=BRIGHT + ", funky dance groove", mood="energetic dance party",
  intro=["Hey hey! It's the Paws and Claws Club!", "Stand up! It's time to dance!"],
  chorus=["Wiggle, wiggle, wiggle your body,", "Dance like nobody's watching, everybody!", "Shake it fast and shake it slow,", "Paws and Claws, let's go, go, go!"],
  verses=[["Rory says shake your head, shake, shake, shake,", "Shake it like the jungle is starting to quake!", "Shake, shake, one, two, three,", "Shake your head along with me!"],
          ["Ziggy says clap your paws, clap, clap, clap,", "Clap them up and clap them in your lap!", "Clap, clap, one, two, three,", "Clap your paws along with me!"],
          ["Waffles says wag your tail, wag, wag, wag,", "Wiggle your bottom, zig and zag!", "Wag, wag, one, two, three,", "Wag your tail along with me!"],
          ["Pebble says stomp your feet, stomp, stomp, stomp,", "Stomp them like a penguin, romp, romp, romp!", "Stomp, stomp, one, two, three,", "Stomp your feet along with me!"]],
  bridge=["Shake your head! Clap your paws!", "Wag your tail! Stomp your feet!", "Faster, faster, everybody now,", "Freeze! And take a bow!"],
  outro="Great dancing! Bye bye, friends!"),
 "ep08-yummy-fruit": dict(bpm=114, inst=BRIGHT, mood="happy",
  intro=["Hey hey! It's the Paws and Claws Club!", "We're hungry! Snack time!"],
  chorus=["Yummy, yummy, yummy in my tummy,", "Fruit is sweet and fruit is funny!", "Crunch it, munch it, one, two, three,", "Yummy fruit for you and me!"],
  verses=[["Rory picks a banana, long and yellow,", "Peel it, peel it, what a funny fellow!", "Munch, munch, one, two, three,", "Banana for Rory, yum yum yummy!"],
          ["Ziggy picks some strawberries red,", "Little seeds on top, she said!", "Nibble, nibble, one, two, three,", "Strawberries for Ziggy, yum yum yummy!"],
          ["Waffles picks a big green apple,", "Crunch, crunch, crunch, he gives a chuckle!", "Crunch, crunch, one, two, three,", "Apple for Waffles, yum yum yummy!"],
          ["Pebble picks some blueberries blue,", "Tiny and round, he eats a few!", "Pop, pop, one, two, three,", "Blueberries for Pebble, yum yum yummy!"]],
  bridge=["Banana! Strawberry! Apple! Blueberry!", "Fruit makes us strong and fruit makes us merry!", "Banana! Strawberry! Apple! Blueberry!", "Rub your tummy, yum yum yummy!"],
  outro="Yummy! Bye bye, friends!"),
 "ep09-rainy-day": dict(bpm=112, inst="bright ukulele, glockenspiel, rain and puddle sound effects, hand claps, bouncy bass, light drums", mood="happy, playful",
  intro=["Hey hey! It's the Paws and Claws Club!", "Pitter patter! It's raining!"],
  chorus=["Pitter patter, rain is falling,", "Puddles, puddles, they are calling!", "Jump in, splash out, one, two, three,", "Rainy day fun for you and me!"],
  verses=[["Rory has a big umbrella,", "Red and round for a lion fella!", "Spin it, spin it, one, two, three,", "Rory stays dry as dry can be!"],
          ["Ziggy wears her purple boots,", "And a raincoat with a hood that's cute!", "Tip toe, tip toe, one, two, three,", "Ziggy hops so carefully!"],
          ["Waffles finds the biggest puddle,", "Splash! Now he's in a muddy muddle!", "Splash, splash, one, two, three,", "Waffles laughs, hee hee hee!"],
          ["Pebble loves the rain the most,", "He slides along from coast to coast!", "Slide, slide, one, two, three,", "Pebble's whizzing happily!"]],
  bridge=["Look up high, the rain has gone,", "The sun comes out to shine upon,", "A rainbow arching in the sky,", "Wave to the clouds and say goodbye!"],
  outro="What a splashy day! Bye bye, friends!"),
 "ep10-goodnight-club": dict(bpm=96, inst="gentle ukulele, soft glockenspiel, music box, warm soft bass, very light percussion",
  mood="gentle, sleepy, warm lullaby feel but still catchy",
  intro=["Hey hey, it's the Paws and Claws Club,", "The stars are out. It's bedtime."],
  chorus=["Goodnight, goodnight, the moon is bright,", "Snuggle up and hold on tight!", "Close your eyes and count to three,", "Sweet dreams for you and me!"],
  verses=[["Rory puts on his star pyjamas,", "Gives a great big yawn, ahhh!", "Yawn, yawn, one, two, three,", "Rory's sleepy as can be!"],
          ["Ziggy curls up in her basket,", "Soft and warm like a fluffy blanket!", "Purr, purr, one, two, three,", "Ziggy's sleepy as can be!"],
          ["Waffles hugs his favourite teddy,", "Fluffs his pillow, now he's ready!", "Snuggle, snuggle, one, two, three,", "Waffles is sleepy as can be!"],
          ["Pebble wraps his yellow scarf,", "Tucks in his flippers with a laugh!", "Shh, shh, one, two, three,", "Pebble's sleepy as can be!"]],
  bridge=["Twinkle, twinkle, little light,", "Owls are hooting in the night,", "The Paws and Claws Club says goodnight,", "Sleep tight, sleep tight."],
  outro="Goodnight, friends. Sweet dreams."),
}


def lyrics(e):
    ch = "\n".join(e["chorus"])
    parts = ["[Intro]\n" + "\n".join(e["intro"]), "[Chorus]\n" + ch]
    for v in e["verses"][:3]:
        parts += ["[Verse]\n" + "\n".join(v), "[Chorus]\n" + ch]
    parts += ["[Verse]\n" + "\n".join(e["verses"][3]), "[Bridge]\n" + "\n".join(e["bridge"]),
              "[Chorus]\n" + ch, "[Chorus]\n" + ch, "[Outro]\n" + e["outro"]]
    return "\n\n".join(parts)


if __name__ == "__main__":
    for i, (name, e) in enumerate(EPS.items()):
        req = {"caption": CAPTION.format(inst=e["inst"], mood=e["mood"]), "lyrics": lyrics(e), "bpm": e["bpm"],
               "duration": 230 if e["bpm"] < 110 else 210, "keyscale": "C major", "timesignature": "4",
               "vocal_language": "en", "lm_batch_size": 2, "seed": 31 + i}
        json.dump(req, open(f"tests/songs/{name}.json", "w"), indent=1)
        json.dump({k: e[k] for k in ("intro", "chorus", "verses", "bridge", "outro")}, open(f"tests/songs/{name}.script.json", "w"), indent=1)
    print("wrote", len(EPS))
