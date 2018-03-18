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
engine = {5: .35, 6:1.20, 7:1.75, 8:2.35, 9:3.60, 10:4.20}

def consumption(weight, distance, warp, ife=0.85):
    if distance < (warp ** 2):
        distance = math.ceil(distance)
    else:
        distance = int(distance)
    return int(math.ceil(weight * distance * engine.get(warp,0) * ife / 200))

class Ship:
    def __init__(self, name, fuel, weight, cargo, pop=0, fuel_prod=0):
        self.name = name
        self.fuel = fuel
        self.weight = weight
        self.cargo=cargo
        self.pop=pop
        self.fuel_prod=fuel_prod
    def __str__(self):
        return "[{name}: fuel={fuel:4d}, wt={weight}, pop={pop}, cargo={cargo}]".format(**self.__dict__)
    def move(self, warp, distance):
        if args.ar:
            losses = int(self.pop * .03)
            self.pop -= losses
        self.fuel -= consumption(self.weight + self.cargo + self.pop, distance, warp) + self.fuel_prod

        
def fleet(*ships):
    return Ship("Fleet", sum(s.fuel for s in ships),
                sum(s.weight for s in ships),
                sum(s.cargo for s in ships),
                sum(s.pop for s in ships),
                fuel_prod=sum(s.fuel_prod for s in ships))
        
def get_time(distance, max_warp=9):
    d = max_warp**2
    time = int(distance) // d
    remainder = distance - (time * d)
    if remainder >= 1: time += 1
    return time

def get_warp(distance, max_warp=9, ce=False):
    time = get_time(distance, max_warp)
    if ce and distance >= 82:
        # prefer ending with a warp 6 jump
        time2 = get_time(distance - 36)
        if time2 + 1 == time:
            distance -= 36
            time -= 1
                        
    maxwarp = math.ceil((int(distance) / time)**.5)
    return min(maxwarp, math.ceil(int(distance)**.5))

mf = Ship("Medium Freighter", 700, 69, 210)
lf = Ship("Large Freighter", 3100, 143, 1200)
hmf = Ship("Heavy Medium Freighter", 450, 71, 260)
ccol = Ship("Cheap Colonizer", 200, 26, 25)
col = Ship("Colonizer", 200, 76, 25)
scout = Ship("Scout", 300, 19, 0)
dxboost = Ship("DD Booster (XRay)", 780, 44, 0)
sfx = Ship("Super Fuel Export", 2250, 123, 0, fuel_prod=200) 

fcol = Ship("Privateer colonizer", 1150, 109, 250)
ffr = Ship("Privateer freighter", 1400, 80, 250)

if __name__ == '__main__':
    

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('distance', type=float)
    parser.add_argument('ships', nargs='+')
    parser.add_argument('--ar', help="Carry AR Population", action='store_true')
    parser.add_argument('--pop',  type=int, help="Amount of population, default=remainder")
    parser.add_argument('--cargo', type=int, default=0, help="Amount of other cargo, default=none")
    parser.add_argument('--fuel',  type=int, default=0, help="Specify fuel")
    parser.add_argument('--ce',  action='store_true', help="Cheap engine, i.e. prefer warp <=6 jump")
    parser.add_argument('--booster', help="Choose booster (e.g. scout, dxboost)")
    args = parser.parse_args()
    print(args)

    flt = fleet()
    distance = args.distance
    for ship in args.ships:
        m = re.match(r"(\d*)(\w+)", ship)
        n, ship = m.groups()
        n = int(n) if n else 1
        ship = locals()[ship]
        #print("Adding {n}x {ship}".format(**locals()))
        flt = fleet(flt, *([ship]*n))

    cap = flt.cargo

    booster = locals()[args.booster] if args.booster else scout
    
    flt.cargo = min(cap, args.cargo)
    flt.pop = cap - flt.cargo
    if args.pop is not None:
        flt.pop = min(flt.pop, args.pop)


    if flt.pop == 25 and args.ar:
        flt.pop = 22 # AR max without loss



    time = get_time(distance)

    print("Moving {distance} ly in {time} turns with {flt}".format(**locals()))

    for nboosters in itertools.count():
        f = fleet(flt, *[booster] * nboosters)
        fuelstart = f.fuel
        nboostersleft = nboosters
        print("\nTrying {nboosters} {booster} boosters: {f}".format(**locals()))
        warps = []
        d = distance

        while d >= 1:
            w = get_warp(d, max_warp=9, ce=args.ce)
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
