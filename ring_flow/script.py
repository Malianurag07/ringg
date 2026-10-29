# Voice-over script for the "Computer Vision for Ring Side Identification and Angular Orientation" video.
# One entry per scene: (on-screen title, [spoken sentences]).
# Spoken text uses US spellings so the TTS pronounces them correctly.
SCRIPT = [
    ("Computer Vision for Ring Side Identification and Angular Orientation", [
        "Hi there.",
        "In the next few minutes, I'll walk you through Computer Vision for Ring Side Identification and Angular Orientation, the system V7 AI Solutions is building with Technocraft.",
        "Just so you know, everything you'll see here is a theoretical estimate, visualized to help us define the scope.",
        "We'll start with how everything gets set up, and then we'll follow a single ring, from the moment it lands on the belt, right up to when the robot drops it onto the pins.",
    ]),
    ("A · Setup: the hardware", [
        "So, first, the hardware.",
        "Above the belt, we've got two cameras, each one in its own vibration-isolated frame, with a light-tight shroud, so stray light from the shop floor doesn't mess with the pictures.",
        "Camera one gets a low-angle ring light, plus a diffuse light. Camera two just gets a diffuse light.",
        "Right before camera one, there's a presence sensor. And if the line doesn't already have a belt encoder, we add one.",
        "Everything connects through an industrial Ethernet switch to the server, which sits in a cooled cabinet, and runs off a UPS.",
        "The M L models themselves are trained beforehand, on a development server with a GPU card, using images of sample rings provided by Technocraft.",
        "V7 AI Solutions specifies all of this hardware, and Technocraft procures it for the line.",
    ]),
    ("A · Setup: teaching the system", [
        "Then there's the one-time software setup.",
        "We photograph a ring of known size, so the system knows exactly how many pixels make a millimeter.",
        "Next, we teach it all five ring types: the outline, the notch layout, and the target angle for each one.",
        "We set the trigger delay, that's the gap between the sensor firing and the camera taking its shot, and we agree on the rotation direction with the Technocraft team.",
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
        "The strobe controller flashes the lights for about point two of a millisecond, which freezes the ring perfectly, even though the belt's still moving.",
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
        "If the side check is clear, the server sends signal one to the line controller. Flip, yes or no.",
        "If it isn't, say the confidence score is too low, or there's no ring, or there are two, the system doesn't guess. It raises an alert, and a diverter flap pushes the ring off into a separate section.",
        "The line controller then tells the flip mechanism what to do. Burr side up? It gets turned over. Rollover side up? It just passes straight through.",
    ]),
    ("B · Camera 2 takes the picture", [
        "Next, camera two has to fire exactly when the ring is centered under it. The line controller doesn't send a trigger for this. Instead, the software takes the moment the flipper was triggered, calculates the delay from there in encoder pulses, and captures the image right on time.",
        "Camera two is also twelve megapixels. Its strobe flashes the diffuse light, which gives us a nice, clean outline of the notches.",
        "And again, the image goes through the switch, to the server.",
    ]),
    ("B · Measuring the angle", [
        "Now we work out the angle.",
        "The software finds the notches, figures out where they're pointing, and calculates how far the ring needs to turn. That's anywhere from zero, up to about eighty-nine degrees, always in the direction we agreed.",
        "The notches are found by an M L model, trained beforehand on images of sample rings provided by Technocraft.",
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
        "We keep an eye on the confidence score over time. If it starts drifting down, maybe because of rust, or a light that's on its way out, we raise an alarm early.",
        "The server and the line controller keep checking on each other with a heartbeat. If that link drops, the line comes to a safe stop.",
        "The operator gets a screen with live status, alerts, and the steps to recover.",
        "And after a fault or a power dip, everything restarts on its own, with the U P S keeping the server running through short power cuts.",
    ]),
    ("B · Ten rings in a row", [
        "Now let's put it all together, and watch ten rings go through the line, one after another.",
        "Each ring is detected by the sensor, gets its ID, and camera one checks which side is up.",
        "Rings that land burr side up get flipped. Rings that are already rollover side up pass straight through.",
        "Camera two measures the angle, and the robot turns each ring and places it in its own slot.",
        "Ten rings. All rollover side up, all at the right angle, each one in its slot.",
    ]),
    ("D · Why the GPU is needed", [
        "So, why do we need a GPU?",
        "Real rings aren't perfect. There's rust, oil, scratches, and lighting that slowly changes over time. An M L model, trained on lots of real ring images, copes with that much better than fixed rules.",
        "These models are trained beforehand, on a development server with a GPU card, using images of sample rings provided by Technocraft.",
        "Training means going through thousands of images, again and again. That's millions of calculations, and a GPU does them in parallel, so training is much, much faster.",
        "On the line, the server's GPU runs the trained models, so each picture is checked in a blink, and just as fast every time, while the processor carries on with the cameras, the signals and the logging.",
        "And when a new ring type comes along, Technocraft provides new sample rings, we capture images of them, retrain the model on the development server, and then update it on the line server.",
        "So the GPU is what makes accurate, reliable M L possible, without ever slowing the line down.",
    ]),
    ("Who owns what", [
        "So, to sum up who does what.",
        "V7 AI Solutions owns all the vision software, from the moment the sensor fires, right through to those two signals.",
        "Technocraft owns the conveyor, the flip mechanism, the robot, the line controller and the pins, and procures all the hardware.",
        "And that's the whole flow. Thanks for watching.",
    ]),
]
