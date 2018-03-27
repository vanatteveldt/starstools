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

# fuel mizer efficiency
# from: view-source:http://craebild.dk/hab_range_tool/fuelusage.html
engines = {'mizer': {'weight': 6, 'eff': [0, 0, 0, 0, .35, 1.20, 1.75, 2.35, 3.60, 4.20]},
           'radram': {'weight': 10, 'eff': [0, 0, 0, 0, 0  , 0   , 1.65, 3.75, 6.00, 7.20]},
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
        self.fuel -= consumption(self.weight + self.cargo + self.pop, distance, warp)
        self.fuel += self.fuel_prod
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
        
def get_time(distance):
    d = args.max_warp**2
    time = int(distance) // d
    remainder = distance - (time * d)
    if remainder >= 1: time += 1
    return time

def get_warp(distance):
    time = get_time(distance)
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
    

#mf = Ship("Medium Freighter", 700, 69, 210)
#col = Ship("Colonizer", 200, 76, 25, col=True)
scout = Ship("Scout", 300, 11, 0)
#dxboost = Ship("DD Booster (XRay)", 780, 44, 0)
#sfx = Ship("Super Fuel Export", 2250, 123, 0, fuel_prod=200, engines=2)
ftrans = Ship("Fuel Transport", 750, 12, 0, fuel_prod=200) 

pcol = Ship("Privateer colonizer", 1150, 103, 250, col=True)
pfr = Ship("Privateer freighter", 1400, 74, 250)

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
    parser.add_argument('--max-warp', "-w", help="Max warp", type=int, default=9)
    
    args = parser.parse_args()

    flt = fleet()
    distance = args.distance
    for ship in args.ships:
        m = re.match(r"(\d*)(\w+)", ship)
        n, ship = m.groups()
        n = int(n) if n else 1
        ship = locals()[ship]
        ship.weight += engines[args.engine]['weight'] * ship.nengines
        #print("Adding {n}x {ship}".format(**locals()))
        flt = fleet(flt, *([ship]*n))

    flt.cap = flt.cargo

    booster = locals()[args.booster] if args.booster else (ftrans if args.inner else scout)

    time = get_time(distance)
    if args.col:
        flt.col = True
    flt.cargo = min(flt.cap, args.cargo)
    flt.pop = flt.cap - flt.cargo
    if args.pop is None:
        if flt.pop == 25 and args.ar:
            flt.pop = 22 # AR max without loss
        if args.inner:
            turns = time - (0 if flt.col else 1)
            if turns:
                flt.pop = get_is_pop(flt.pop, turns)
            print("IS pop to board", flt.pop, flt.col and " (Colonizers, so full on arrival)" or " (Freighters, so full turn before arrival)")
    else:
        flt.pop = min(flt.pop, args.pop)
        

    print("Moving {distance} ly in {time} turns with {flt}".format(**locals()))

    for nboosters in itertools.count():
        f = fleet(flt, *[booster] * nboosters)
        fuelstart = f.fuel
        nboostersleft = nboosters
        print("\nTrying {nboosters} {booster} boosters: {f}".format(**locals()))
        warps = []
        d = distance

        while d >= 1:
            w = get_warp(d)
            warps.append(w)
            travel = min(d, w**2)
            d = max(0, d - w**2)
            if d < 1:
                travel += d
                d = 0
            f.move(w, travel)
            if f.fuel < 0:
                print("Fleet ran out of fuel, trying with more boosters...")
                break


            print("Moved {travel:1.2f} at warp {w}, {f}, distance to go: {d:1.2f}"
                  .format(**locals()))
            if d >= 1:
                # can we send boosters home?
                booster_fuel = sum(consumption(booster.weight, wr**2, wr) for wr in warps)
                consumed = fuelstart - f.fuel
                nover = min(nboostersleft, consumed // (booster.fuel - booster_fuel))
                booster_fuel *= nover
                if nover and not booster.fuel_prod:
                    f.fuel -= booster_fuel
                    f.weight -= nover * booster.weight
                    nboostersleft -= nover
                    print("{nover} boosters leave with {booster_fuel} fuel, left: {f}".format(**locals()))

        if f.fuel >= 0:
            break

    print("\nArrived! {} boosters, jumps: {}, fuel consumed {}, left {}"
          .format(nboosters, warps, fuelstart - f.fuel, f.fuel))
