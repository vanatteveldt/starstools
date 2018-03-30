#!/usr/bin/python3
"""
Simple utility for computing fuel requirements and boosters

You probably need to edit ships, engine etc to fill your needs.
Is aware of AR pop decay, but not yet of IS pop growth
"""

import math
import itertools
import copy
import sys
import argparse
import re
import logging

# fuel mizer efficiency
# from: view-source:http://craebild.dk/hab_range_tool/fuelusage.html
engines = {'mizer': {'weight': 6, 'eff': [0, 0, 0, 0, .35, 1.20, 1.75, 2.35, 3.60, 4.20]},
           'radram': {'weight': 10, 'eff': [0, 0, 0, 0, 0  , 0   , 1.65, 3.75, 6.00, 7.20]},
           'lh6': {'weight': 9, 'eff': [0,.20,.60,1.00,1.00,1.05,4.50,7.50,9.00,10.80]},
           'dll7': {'weight': 13, 'eff': [0,.20,.60,.70,1.00,1.00,1.10,6.00,7.50,9.00]},
          }

def consumption(weight, distance, warp):
    if distance < (warp ** 2):
        distance = math.ceil(distance)
    else:
        distance = int(distance)
    eff = engines[args.engine]['eff'][int(warp)-1] * (1 if args.noife else 0.85)
    return int(math.ceil(weight * distance * eff / 200))

class Ship:
    def __init__(self, name, fuel, weight, cargo, cap=None, pop=0, fuel_prod=0, col=False, nengines=1):
        self.name = name
        self.fuel = fuel
        self.weight = weight
        self.cargo=cargo
        self.pop=pop
        self.fuel_prod=fuel_prod
        self.cap=(cargo + pop if cap is None else cap)
        self.col = col
        self.nengines=nengines
    def __str__(self):
        return "[{name}: fuel={fuel:4d}, wt={weight}, pop={pop}, cargo={cargo}, cap={cap}, col={col}, fuel_prod={fuel_prod}]".format(**self.__dict__)
    def move(self, warp, distance):
        if args.ar:
            losses = int(self.pop * .03)
            self.pop -= losses
        wt = self.weight + self.cargo + self.pop
        fcon = consumption(wt, distance, warp)
        #print("Moved {distance}@W{warp}, fuel use {fcon} out of {self.fuel} (weight:{wt})".format(**locals()))
        self.fuel += self.fuel_prod - fcon
        if args.inner:
            self.pop=grow_is(self.pop, self.cap - self.cargo)
            


def fleet(*ships):
    return Ship("Fleet",
                fuel=sum(s.fuel for s in ships),
                weight=sum(s.weight for s in ships),
                cargo=sum(s.cargo for s in ships),
                pop=sum(s.pop for s in ships),
                cap=sum(s.cap for s in ships),
                fuel_prod=sum(s.fuel_prod for s in ships),
                col=any(s.col for s in ships))
        
def get_time(distance, max_warp=9):
    d = max_warp**2
    time = int(distance) // d
    remainder = distance - (time * d)
    if remainder >= 1: time += 1
    return time

def get_warp(distance, max_warp=9):
    time = get_time(distance, max_warp=max_warp)
    if args.ce and distance >= 82:
        # prefer ending with a warp 6 jump
        time2 = get_time(distance - 36)
        if time2 + 1 == time:
            distance -= 36
            time -= 1
                        
    maxwarp = math.ceil((int(distance) / time)**.5)
    return min(maxwarp, math.ceil(int(distance)**.5))

def grow_is(pop, cap, nturns=1):
    gr = int(args.inner/2) / 100.
    pop += int(pop * gr)
    if nturns > 1:
        pop = grow_is(pop, cap, nturns=nturns-1)
    return min(pop, cap)

def get_is_pop(cap, turns):
    growth = 1 + int(args.inner/2)/100.
    result = int(cap / growth**turns)
    while grow_is(result, cap, turns) < cap:
        result += 1
    
    return result
    
def go(flt, distance, nboosters=0, maxwarp=9, indent=0):
    log=lambda *x: print(" . "*indent, *x, sep='') if args.verbose and indent==0 else lambda *x: None
    booster = getattr(Ships, args.booster) if args.booster else (Ships.ftrans if args.inner else Ships.scout)

    f = fleet(flt, *[booster] * nboosters)
    fuelstart = f.fuel
    if nboosters:
        log("\nTrying {nboosters} {booster} boosters: {f}".format(**locals()))
    warps = []
    boosters = []

    while distance >= 1:
        w = get_warp(distance, max_warp=maxwarp)
        warps.append(w)
        boosters.append(nboosters)
        travel = min(distance, w**2)
        distance = max(0, distance - w**2)
        if distance < 1:
            travel += distance
            distance = 0
        f.move(w, travel)
        if f.fuel < 0:
            log("Fleet ran out of fuel, try with more boosters...")
            return None, None


        log("Moved {travel:1.2f} at warp {w}, {f}, distance to go: {distance:1.2f}"
              .format(**locals()))
        if distance >= 1 and nboosters > 1:
            # can we send boosters home?
            booster_fuel = sum(consumption(booster.weight, wr**2, wr) for wr in warps)
            for nover in range(nboosters - 1, 0, -1):
                # can we send #nover boosters home?
                f2 = fleet(f)
                f2.fuel -= nover * booster_fuel
                f2.weight -= nover * booster.weight
                w,b =  go(f2, distance, maxwarp=maxwarp, indent=indent+1)
                if w:
                    nhome = nboosters - nover
                    log("Only need ", nover, "boosters, sending ", nhome, " home")
                    f.fuel -= nover * booster_fuel
                    f.weight -= nover * booster.weight
                    nboosters -= nover
                    break
                    #log("{nover} boosters leave with {booster_fuel} fuel, left: {f}".format(**locals()))
    return warps, boosters

class Ships:
    mf = Ship("Medium Freighter", 700, 63, 210)
    #col = Ship("Colonizer", 200, 76, 25, col=True)
    scout = Ship("Scout", 300, 11, 0)
    #dxboost = Ship("DD Booster (XRay)", 780, 44, 0)
    ftrans = Ship("Fuel Transport", 750, 12, 0, fuel_prod=200) 
    
    pcol = Ship("Privateer colonizer", 1150, 103, 250, col=True)
    pfr = Ship("Privateer freighter", 1400, 74, 250)
    hpf = Ship("Heavy privateer freighter", 650, 80, 400)
    mpf = Ship("Medium privateer freighter", 900, 80, 350)

    lf = Ship("Large Freighter", 3100, 131, 1200, nengines=2)
    sfx = Ship("Super Fuel Export", 2250, 111, 0, fuel_prod=200, nengines=2)

if __name__ == '__main__':
    

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('distance', type=float)
    parser.add_argument('ships', nargs='+')
    parser.add_argument('--ar', help="Carry AR Population", action='store_true')
    parser.add_argument('--engine', help="Engine", default='mizer', choices=engines.keys())
    parser.add_argument('--no-ife', help="No IFE", action='store_true', dest='noife')
    parser.add_argument('--is', help="Carry IS Population (provide PGR)", default=20, dest='inner', type=int)
    parser.add_argument('--pop',  type=int, help="Amount of population, default=remainder")
    parser.add_argument('--col', help="Set fleet to colonizing (i.e. IS full on arrival)", action='store_true')
    parser.add_argument('--cargo', type=int, default=0, help="Amount of other cargo, default=none")
    parser.add_argument('--fuel',  type=int, default=0, help="Specify fuel")
    parser.add_argument('--ce',  action='store_true', help="Cheap engine, i.e. prefer warp <=6 jump")
    parser.add_argument('--booster', help="Choose booster (e.g. scout, dxboost)")
    parser.add_argument('--verbose', action='store_true')
    
    
    args = parser.parse_args()

    flt = fleet()
    distance = args.distance
    for ship in args.ships:
        m = re.match(r"(\d*)(\w+)", ship)
        n, ship = m.groups()
        n = int(n) if n else 1
        ship = getattr(Ships, ship)
        ship.weight += engines[args.engine]['weight'] * ship.nengines
        #print("Adding {n}x {ship}".format(**locals()))
        flt = fleet(flt, *([ship]*n))

    flt.cap = flt.cargo

    if args.col:
        flt.col = True
    flt.cargo = min(flt.cap, args.cargo)
    flt.pop = flt.cap - flt.cargo
    if args.pop is None:
        if flt.pop == 25 and args.ar:
            flt.pop = 22 # AR max without loss
    else:
        flt.pop = min(flt.pop, args.pop)
        

    prev_nbooster = None
    if args.inner and not args.pop:
        print("Computing IS pop",  flt.col and " (Colonizers, so full on arrival)" or " (Freighters, so full turn before arrival)")
    for maxwarp in [9,8,7]:
        time = get_time(distance, max_warp=maxwarp)
        f = fleet(flt)
        if args.inner and not args.pop:
            turns = time - (0 if flt.col else 1)
            if turns:
                ispop = get_is_pop(flt.pop, turns)
                f.pop = ispop
            else:
                ispop = flt.pop
                                
        else:
            ispop = None
        
        for nboosters in itertools.count():
            if nboosters > 10:
                print("Tried {nboosters} boosters at warp {maxwarp}, giving up".format(**locals()))
                break
            warps, boosters = go(f, distance, nboosters, maxwarp)
            if warps:
                if (prev_nbooster is None) or nboosters < prev_nbooster:
                    print("Warps: ", warps, "Boosters:", boosters, "IS Pop", ispop)
                prev_nbooster = nboosters
                break
        
    
