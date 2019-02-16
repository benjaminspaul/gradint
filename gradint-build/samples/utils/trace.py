
# trace.py: script to generate raytraced animations of Gradint lessons
# Version 1.1 (c) 2018-19 Silas S. Brown.  License: GPL

#  The Disney Pixar film "Inside Out" (2015) represented
#  memories as spheres.  I don't have their CGI models, but
#  we can do spheres in POV-Ray and I believe that idea is
#  simple enough to be in the public domain (especially if
#  NOT done like Pixar did it) - hopefully this might show
#  some people how Gradint's method is supposed to work
#  (especially if they've seen the Inside Out film).

# This script generates the POV-Ray scenes from a lesson.
# Gradint is run normally (passing any command-line arguments on,
# must include outputFile so audio can be included in the animation)
# and then the animation is written to /tmp/gradint.mp4.

# Requires POV-Ray, ffmpeg, and the Python packages vapory
# and futures (use sudo pip install futures vapory) -
# futures is used to run multiple instances of POV-Ray on
# multi-core machines.

debug_one_frame_only = False

import sys,os,traceback
oldName = __name__ ; from vapory import * ; __name__ = oldName
from concurrent.futures import ProcessPoolExecutor

assert os.path.exists("gradint.py"), "You must move trace.py to the top-level Gradint directory and run it from there"
import gradint
assert gradint.outputFile, "You must run trace.py with gradint parameters that include outputFile"

class MovableParam:
    def __init__(self): self.fixed = []
    def fixAt(self,t,value):
        while any(x[0]==t and not x[1]==value for x in self.fixed): t += 0.2
        self.fixed.append((t,value))
    def getPos(self,t):
        assert self.fixed, "Should fixAt before getPos"
        self.fixed.sort()
        for i in xrange(len(self.fixed)):
            if self.fixed[i][0] >= t:
                if i: # interpolate
                    if self.fixed[i-1][1]==None: return None
                    duration = self.fixed[i][0]-self.fixed[i-1][0]
                    progress = t-self.fixed[i-1][0]
                    return (self.fixed[i][1]*progress + self.fixed[i-1][1]*(duration-progress))*1.0/duration
                else: return self.fixed[i][1] # start position
        return self.fixed[-1][1]

class MovablePos:
    def __init__(self): self.x,self.y,self.z = MovableParam(),MovableParam(),MovableParam()
    def fixAt(self,t,*args):
        if args[0]==None: x=y=z=None
        else: x,y,z = args
        self.x.fixAt(t,x),self.y.fixAt(t,y),self.z.fixAt(t,z)
    def getPos(self,t):
        r=(self.x.getPos(t),self.y.getPos(t),self.z.getPos(t))
        if r==(None,None,None): return None
        else: return r

SceneObjects = set()

class MovableSphere(MovablePos):
    def __init__(self,radius=0.5,colour="prompt",imageFilename=None):
        MovablePos.__init__(self)
        self.colour = colour
        self.imageFilename = imageFilename
        self.radius = MovableParam()
        self.radius.fixAt(-1,radius)
        SceneObjects.add(self)
    # fixAt(t,x,y,z) inherited
    def obj(self,t):
        pos = self.getPos(t)
        if not pos: return # not in scene at this time
        r = self.radius.getPos(t)
        if self.imageFilename: return Sphere(list(pos),r,colour(self.colour),Texture(Pigment(ImageMap('"'+self.imageFilename+'"',"once","interpolate 2","transmit all 0.3"),'scale',[1.5*r,1.5*r,1],'translate',list(pos),'translate',[-.75*r,-.75*r,0])))
        else: return Sphere(list(pos),r,colour(self.colour))

class ObjCollection:
    def __init__(self): self.objs = set()
    def add(self,obj,dx,dy,dz): self.objs.add((obj,dx,dy,dz))
    def get(self,dx,dy,dz): # should be small so:
        for o,ddx,ddy,ddz in self.objs:
            if (ddx,ddy,ddz) == (dx,dy,dz): return o
    def fixAt(self,t,*args):
        if args[0]==None: x=y=z=None
        else: x,y,z = args
        for obj,dx,dy,dz in self.objs:
            if args==[None]: obj.fixAt(t,None,None,None)
            else: obj.fixAt(t,x+dx,y+dy,z+dz)

eventTrackers = {}
def EventTracker(rowNo,imageFilename=None):
    if not rowNo in eventTrackers:
        eventTrackers[rowNo] = ObjCollection()
        eventTrackers[rowNo].add(MovableSphere(1,"l1",imageFilename),-1,0,0)
        eventTrackers[rowNo].add(MovableSphere(1,"l2",imageFilename),+1,0,0)
        eventTrackers[rowNo].numRepeats = 0
    return eventTrackers[rowNo]
rCache = {}
def repeatSphere(rowNo,numRepeats=0):
    if not (rowNo,numRepeats) in rCache:
        rCache[(rowNo,numRepeats)] = MovableSphere(0.1,"prompt")
    return rCache[(rowNo,numRepeats)]
def addRepeat(rowNo,t=0,length=0):
    et = EventTracker(rowNo)
    rpt = repeatSphere(rowNo,et.numRepeats)
    if length:
        rpt.fixAt(-1,None) # not exist yet (to save a tiny bit of POVRay computation)
        rpt.fixAt(t-1,4*rowNo+1,0,61) # behind far wall
        rpt.fixAt(t,4*rowNo-1,0,0) # ready to be 'batted'
        et.fixAt(t,4*rowNo,0,10) # we're at bottom
        camera_lookAt.fixAt(t,4*rowNo,0,10)
        camera_lookAt.fixAt(t+length,4*rowNo,10,10)
        camera_position.x.fixAt(t+length/2.0,4*rowNo)
        # careful with Y : try to avoid sudden vertical motion between 2 sequences
        camera_position.y.fixAt(t+length*.2,1)
        camera_position.y.fixAt(t+length*.8,4)
        camera_position.z.fixAt(t+length*.2,-10)
        camera_position.z.fixAt(t+length*.8,-5)
    et.add(rpt,0,1+0.2*et.numRepeats,0) # from now on we keep this marker
    et.fixAt(t+length,4*rowNo,10,10) # at end of repeat (or at t=0) we're at top, and the repeat marker is in place
    et.numRepeats += 1

camera_position = MovablePos()
camera_lookAt = MovablePos()
def cam(t): return Camera('location',list(camera_position.getPos(t)),'look_at',list(camera_lookAt.getPos(t)))
def lights(t): return [LightSource([camera_position.x.getPos(t)+10, 15, -20], [1.3, 1.3, 1.3])]

def colour(c): return Texture(Pigment('color',{"l1":[.8,1,.2],"l2":[.5,.5,.9],"prompt":[1,.6,.5]}[c])) # TODO: better colours
wall,ground = Plane([0, 0, 1], 60, Texture(Pigment('color', [1, 1, 1])), Finish('ambient',0.9)),Plane( [0, 1, 0], -1, Texture( Pigment( 'color', [1, 1, 1]), Finish( 'phong', 0.1, 'reflection',0.4, 'metallic', 0.3))) # from vapory example
def scene(t):
    """ Returns the scene at time 't' (in seconds) """
    return Scene(cam(t), lights(t) + [wall,ground] + [o for o in [x.obj(t) for x in SceneObjects] if not o==None])

def Event_draw(self,startTime,rowNo,inRepeat): pass
gradint.Event.draw = Event_draw

def CompositeEvent_draw(self,startTime,rowNo,inRepeat):
  if self.eventList:
    t = startTime
    for i in self.eventList:
      i.draw(t,rowNo,True)
      t += i.length
    if inRepeat: return
    # Call addRepeat, but postpone the start until the
    # first loggable event, to reduce rapid camera mvt
    st0 = startTime
    for i in self.eventList:
      if i.makesSenseToLog(): break
      else: startTime += i.length
    if startTime==t: startTime = st0 # shouldn't happen
    addRepeat(rowNo,startTime,t-startTime)
gradint.CompositeEvent.draw=CompositeEvent_draw

def Event_colour(self,language):
    if self.makesSenseToLog():
      if language==gradint.firstLanguage: return "l1"
      else: return "l2"
    else: return "prompt"
gradint.Event.colour = Event_colour

def eDraw(startTime,length,rowNo,colour):
    minR = 0.5
    if colour=="l1":
        r = EventTracker(rowNo).get(-1,0,0).radius
    elif colour=="l2":
        r = EventTracker(rowNo).get(+1,0,0).radius
    else:
        r = repeatSphere(rowNo,EventTracker(rowNo).numRepeats).radius
        minR = 0.1
    maxR = min(max(length,minR*1.5),minR*3) # TODO: vary with event's volume, so cn see the syllables? (partials can do that anyway)
    r.fixAt(startTime,minR)
    r.fixAt(startTime+length,minR)
    if length/2.0 > 0.5:
        r.fixAt(startTime+0.5,maxR)
        # TODO: wobble in the middle?
        r.fixAt(startTime+length-0.5,maxR)
    else: r.fixAt(startTime+length/2.0,maxR)

def SampleEvent_draw(self,startTime,rowNo,inRepeat):
    if self.file.startswith(gradint.partialsDirectory): l=self.file.split(os.sep)[1]
    else: l = gradint.languageof(self.file)
    eDraw(startTime,self.length,rowNo,self.colour(l))
gradint.SampleEvent.draw = SampleEvent_draw
def SynthEvent_draw(self,startTime,rowNo,inRepeat): eDraw(startTime,self.length,rowNo,self.colour(self.language))
gradint.SynthEvent.draw = SynthEvent_draw

def sgn(i):
    if i>0: return 1
    elif i<0: return -1
    else: return 0

def byFirstLen(e1,e2):
    r = e1[0].glue.length+e1[0].glue.adjustment-e2[0].glue.length-e2[0].glue.adjustment
    # but it must return int not float, so
    return sgn(r)
def byStart(e1,e2): return sgn(e1.start-e2.start)

def runGradint():
  gradint.gluedListTracker=[]
  gradint.waitBeforeStart=0
  gradint.main()
  gradint.gluedListTracker.sort(byFirstLen)
  duration = 0
  for l,row in zip(gradint.gluedListTracker,xrange(len(gradint.gluedListTracker))):
    def check_for_pictures():
     for gluedEvent in l:
      event = gluedEvent.event
      try: el=event.eventList
      except: el=[event]
      for j in el:
       try: el2=j.eventList
       except: el2=[j]
       for i in el2:
        if hasattr(i,"file") and "_" in i.file:
         for imgExt in ["gif","png","jpeg","jpg"]:
          imageFilename = i.file[:i.file.rindex("_")]+os.extsep+imgExt # TODO: we're assuming no _en etc in the image filename (projected onto both L1 and L2)
          if os.path.exists(imageFilename):
              return EventTracker(row,os.path.abspath(imageFilename))
    check_for_pictures()
    if hasattr(l[0],"timesDone"): timesDone = l[0].timesDone
    else: timesDone = 0
    for i in xrange(timesDone): addRepeat(row)
    glueStart = 0
    for i in l:
      i.event.draw(i.getEventStart(glueStart),row,False)
      glueStart = i.getAdjustedEnd(glueStart)
      duration = max(duration,glueStart)
  return duration

theFPS = 15 # 10 is insufficient for fast movement

def tryFrame((frame,numFrames)):
    print "Making frame",frame,"of",numFrames
    try:
        try: os.mkdir("/tmp/"+repr(frame)) # vapory writes a temp .pov file and does not change its name per process, so better be in a process-unique directory
        except: pass
        os.chdir("/tmp/"+repr(frame))
        scene(frame*1.0/theFPS).render(width=640, height=480, antialiasing=0.3, outfile="/tmp/frame%05d.png" % frame)
        # antialiasing=0.001 ? (left at None doesn't look very good at 300x200, cld try at 640x480 or 1280x720) (goes to the +A param, PovRay default is 0.3 if -A specified without param; supersample (default 9 rays) if colour differs from neighbours by this amount)
        # TODO: TURN OFF JITTER with -J if using anti-aliasing in animations
        # quality? (+Q, 1=ambient light only, 2=lighting, 4,5=shadows, 8=reflections 9-11=radiosity etc, default 9)
        os.chdir("/tmp") ; os.system('rm -r '+repr(frame))
        return None
    except:
        if frame==0: raise
        traceback.print_exc()
        sys.stderr.write("Frame %d render error, will skip\n" % frame)
        return "cp /tmp/frame%05d.png /tmp/frame%05d.png" % (frame-1,frame)

def main():
    executor = ProcessPoolExecutor()
    duration = runGradint()
    numFrames = int(duration*theFPS)
    # TODO: pickle all MovableParams so can do the rendering on a different machine than the one that makes the Gradint lesson?
    if debug_one_frame_only: numFrames,cmds = 0,[tryFrame((0,1)),"open /tmp/frame00000.png"] # TODO: 'open' assumes Mac
    else: cmds = list(executor.map(tryFrame,[(frame,numFrames) for frame in xrange(numFrames)]))+["ffmpeg -y -framerate "+repr(theFPS)+" -i /tmp/frame%05d.png -i "+gradint.outputFile+" -movflags faststart -pix_fmt yuv420p /tmp/gradint.mp4"] #  (could alternatively run with -vcodec huffyuv /tmp/gradint.avi for lossless, insead of --movflags etc, but will get over 6 gig and may get A/V desync problems in mplayer/VLC that -delay doesn't fix, however -b:v 1000k seems to look OK; for WeChat etc you need to recode to h.264, and for HTML 5 video need recode to WebM (but ffmpeg -c:v libvpx no good if not compiled with support for those libraries; may hv to convert on another machine i.e. ffmpeg -i gradint.mp4 -vf scale=320:240 -c:v libvpx -b:v 500k gradint.webm))
    for c in cmds:
        # patch up skipped frames, then run ffmpeg (or debug_one_frame_only show the single frame)
        if c:
            print c ; os.system(c)
    for f in xrange(numFrames): os.remove("/tmp/frame%05d.png" % f) # wildcard from command line could get 'argument list too long' on BSD etc
if __name__=="__main__": main()
else: print __name__
