#!/usr/bin/env python3.7

# Copyright 2022, Gurobi Optimization, LLC

# Solve a traveling salesman problem on a randomly generated set of
# points using lazy constraints.   The base MIP model only includes
# 'degree-2' constraints, requiring each node to have exactly
# two incident edges.  Solutions to this model may contain subtours -
# tours that don't visit every city.  The lazy constraint callback
# adds new constraints to cut them off.

import sys
import math
import random
from itertools import combinations
import gurobipy as gp
from gurobipy import GRB


def subtourelim_updated(model, where):
    subtourelim1(model, where)
    subtourelim2(model, where)


# Callback - use lazy constraints to eliminate sub-tours
def subtourelim1(model, where):
    if where == GRB.Callback.MIPSOL:
        vals = model.cbGetSolution(model._edges1)
        # find the shortest cycle in the selected edge list
        tour = subtour(vals)
        if len(tour) < n:
            # add subtour elimination constr. for every pair of cities in tour
            model.cbLazy(gp.quicksum(model._edges1[i, j] for i, j in combinations(tour, 2)) <= len(tour)-1)

# Callback - use lazy constraints to eliminate sub-tours
def subtourelim2(model, where):
    if where == GRB.Callback.MIPSOL:
        vals = model.cbGetSolution(model._edges2)
        # find the shortest cycle in the selected edge list
        tour = subtour(vals)
        if len(tour) < n:
            # add subtour elimination constr. for every pair of cities in tour
            model.cbLazy(gp.quicksum(model._edges2[i, j] for i, j in combinations(tour, 2)) <= len(tour)-1)



# Given a tuplelist of edges, find the shortest subtour

def subtour(vals):
    # make a list of edges selected in the solution
    edges = gp.tuplelist((i, j) for i, j in vals.keys() if vals[(i, j)] > 0.5)

    unvisited = list(range(n))
    cycle = range(n+1)  # initial length has 1 more city
    while unvisited:  # true if list is non-empty
        thiscycle = []
        neighbors = unvisited
        while neighbors:
            current = neighbors[0]
            thiscycle.append(current)
            unvisited.remove(current)
            neighbors = [j for i, j in edges.select(current, '*')
                         if j in unvisited]
        if len(cycle) > len(thiscycle):
            cycle = thiscycle
    return cycle


# Parse argument

print("usage: fisrt argument is the number of vertex and second is the parameter k\n\n")

if len(sys.argv) < 3:
    print('Usage: tsp.py npoints')
    sys.exit(1)

n = int(sys.argv[1])
k = int(sys.argv[2])

print(">> vertex number: {}".format(n))
print(">> k number: {}".format(k))

# Create n random points

random.seed(1)

points1 = [(random.randint(0, 100), random.randint(0, 100)) for i in range(n)]
points2 = [(random.randint(0, 100), random.randint(0, 100)) for i in range(n)]


# Dictionary of Euclidean distance between each pair of points

dist1 = {(i, j):
        math.sqrt(sum((points1[i][w]-points1[j][w])**2 for w in range(2)))
        for i in range(n) for j in range(i)}

dist2 = {(i, j):
        math.sqrt(sum((points2[i][w]-points2[j][w])**2 for w in range(2)))
        for i in range(n) for j in range(i)}


m = gp.Model()

m.setParam('TimeLimit', 60*30) # in seconds


# Create variables
edges1 = m.addVars(dist1.keys(), obj=dist1, vtype=GRB.BINARY, name='edges1')
for i,j in edges1.keys():
    edges1[j,i] = edges1[i,j]


edges2 = m.addVars(dist2.keys(), obj=dist2, vtype=GRB.BINARY, name='edges2')
for i,j in edges2.keys():
    edges2[j,i] = edges2[i,j]



# just getting the indices from edges - can be dist1.keys() or dist2.keys()
duplication = m.addVars(dist1.keys(), vtype=GRB.BINARY, name='duplication')

m.addConstrs(edges1.sum(i, '*') == 2 for i in range(n))
m.addConstrs(edges2.sum(i, '*') == 2 for i in range(n))
m.addConstr(duplication.sum() >= k)


for i in range(n):
    for j in range(i):
        m.addConstr(edges1[i,j] + edges2[i,j] >= 2 * duplication[i,j])

# Optimize model
m._edges1 = edges1
m._edges2 = edges2
m.Params.LazyConstraints = 1
m.optimize(subtourelim_updated)


tour_tsp1 = subtour(m.getAttr('X', edges1))
assert len(tour_tsp1) == n

print('\n')
print('TSP_1:')
print('Optimal tour: %s' % str(tour_tsp1))
# print('Optimal cost: %g' % m.ObjVal) ------ adjust later
print('')



tour_tsp2 = subtour(m.getAttr('X', edges2))
assert len(tour_tsp2) == n

print('\n')
print('TSP_2:')
print('Optimal tour: %s' % str(tour_tsp2))
# print('Optimal cost: %g' % m.ObjVal) ------ adjust later
print('')


count_k = 0

for i in range(n):
    for j in range(n):
        next_i = (i+1)%n
        next_j = (j+1)%n

        edge1 = [tour_tsp1[i], tour_tsp1[next_i]]
        edge1.sort()
        edge2 = [tour_tsp2[j], tour_tsp2[next_j]]
        edge2.sort()
        
        if edge1 == edge2:
            count_k += 1

print("count_k: {}".format(count_k))