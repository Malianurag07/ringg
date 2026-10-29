# Voice-over script for the ring orientation cell walkthrough.
# One entry per scene: (on-screen title, [spoken sentences]).
# Spoken text uses US spellings so the TTS pronounces them correctly.
SCRIPT = [
    ("Ring orientation cell", [
        "Hi there.",
        "In the next few minutes, I'll walk you through the ring orientation cell we're building with Technocraft.",
        "We'll start with how everything gets set up, and then we'll follow a single ring, from the moment it lands on the belt, right up to when the robot drops it onto the pins.",
    ]),
    ("A · Setup: the hardware", [
        "So, first, the hardware.",
        "Above the belt, we've got two cameras, each one in its own vibration-isolated frame, with a light-tight shroud, so stray light from the shop floor doesn't mess with the pictures.",
        "Camera one gets a low-angle ring light, plus a diffuse light. Camera two just gets a diffuse light.",
        "Right before camera one, there's a presence sensor. And if the line doesn't already have a belt encoder, we add one.",
        "Everything connects through an industrial Ethernet switch to the AI server, which sits in a cooled cabinet, and runs off a UPS.",
        "We specify all of this. Technocraft buys it, and does the electrical work.",
    ]),
    ("A · Setup: teaching the system", [
        "Then there's the one-time software setup.",
        "We photograph a ring of known size, so the system knows exactly how many pixels make a millimeter.",
        "Next, we teach it all five ring types: the outline, the notch layout, and the target angle for each one.",
        "We set the trigger delay, that's the gap between the sensor firing and the camera taking its shot, and we agree on the rotation direction with the robotics team.",
        "And finally, we set up the signal link with the line controller, including what every signal means, and what should happen if that link ever drops.",
    ]),
    ("B · A ring arrives", [
        "Okay. Now let's follow a ring through. A new one shows up roughly every six seconds.",
        "It lands on the belt at a random spot, and it could be either side up.",
        "As its front edge breaks the sensor's light beam, the sensor sends a pulse straight to camera one's trigger input.",
        "At the same moment, our software logs the event, gives the ring an ID number, and adds it to the count.",
        "Then we wait for the ring to reach the center of the camera's view. Depending on belt speed, that's somewhere between about half a second and two and a half seconds, counted in encoder pulses.",
    ]),
    ("B · Camera 1 takes the picture", [
        "Once it's centered, camera one fires.",
        "The strobe controller flashes both lights for about point two of a millisecond, which freezes the ring perfectly, even though the belt's still moving.",
        "That low-angle light skims across the surface, so the burr edge really stands out.",
        "The twelve-megapixel image then travels through the switch, to the server's camera network card. That takes about a tenth of a second.",
    ]),
    ("B · The server checks the image", [
        "Now the server takes a look.",
        "First, is there exactly one complete ring in the picture? Not zero, not two, and not half a ring, cut off at the edge.",
        "Then, where is it, and which of the five types is it?",
        "And the big one: is the burr side or the rollover side facing up, and how sure are we about that?",
        "All of this happens in under a second.",
    ]),
    ("B · Signal 1 and the flip", [
        "If we're confident, the server sends signal one to the line controller. Flip, yes or no.",
        "If we're not, say the confidence is low, or there's no ring, or there are two, we don't guess. We raise an alert, and the ring gets diverted, the line stops, or an operator checks it. Whichever we've agreed on.",
        "The line controller then tells the flip mechanism what to do. Burr side up? It gets turned over. Rollover side up? It just passes straight through.",
    ]),
    ("B · Camera 2 takes the picture", [
        "When the flip cycle ends, the line controller sends a trigger to camera two. Or, if we've fitted one, a second presence sensor does that job.",
        "Camera two is also twelve megapixels. Its strobe flashes the diffuse light, which gives us a nice, clean outline of the notches.",
        "And again, the image goes through the switch, to the server.",
    ]),
    ("B · Measuring the angle", [
        "Now we work out the angle.",
        "The software finds the notches, figures out where they're pointing, and calculates how far the ring needs to turn. That's anywhere from zero, up to about eighty-nine degrees, always in the direction we agreed.",
        "As for exactly how we find those notches, it'll either be a trained M L model, or classic image processing with Open C V. We'll make that call once we've tested both on real rings.",
        "Either way, the result gets matched back to the ring's ID from the sensor, so the right angle always goes with the right ring.",
    ]),
    ("B · Signal 2 and the robot", [
        "Then comes signal two. The rotation angle goes out to the line controller, or straight to the robot.",
        "The robot picks up the ring, turns it by exactly that angle, and places it onto the pins.",
        "And that's one ring done. About six seconds later, the next one comes along, and the whole thing happens again.",
    ]),
    ("C · Running in the background", [
        "While all that's going on, a few things are running in the background, all the time.",
        "Every image, every decision, every confidence score and every signal is saved against the ring's ID, so we can trace anything later.",
        "We compare the sensor count with the number of rings we actually processed, so a missed ring never slips by unnoticed.",
        "We keep an eye on confidence over time. If it starts drifting down, maybe because of rust, or a light that's on its way out, we raise an alarm early.",
        "The server and the line controller keep checking on each other with a heartbeat. If that link drops, the line comes to a safe stop.",
        "The operator gets a screen with live status, alerts, and the steps to recover.",
        "And after a fault or a power dip, everything restarts on its own, with the U P S keeping the server running through short power cuts.",
    ]),
    ("D · Why the GPU is needed", [
        "So, why is there a GPU in the server?",
        "For a lot of this, classic image processing on the processor does the job. But real rings aren't perfect. There's rust, oil, scratches, and lighting that slowly changes over time.",
        "If testing shows that a trained M L model handles that better, whether it's for the side check or for finding the notches on camera two, then the GPU is what runs it.",
        "A model like that means millions of calculations on every image. The GPU does them in parallel, so each picture is done in a blink, and just as fast every single time, while the processor carries on with the cameras, the signals and the logging.",
        "It also lets us retrain the model right there on site, when a new ring type comes in or conditions change. Nothing ever has to leave the factory.",
        "So, basically, the GPU gives us the headroom to go with whichever method works best, without ever slowing the line down.",
    ]),
    ("Who owns what", [
        "So, to sum up who does what.",
        "V seven A I owns all the vision software, from the moment the sensor fires, right through to those two signals.",
        "Technocraft owns the conveyor, the flip mechanism, the robot, the line controller and the pins, and buys all the hardware.",
        "And that's the whole flow. Thanks for watching.",
    ]),
]
