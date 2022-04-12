import sys
import math
import random
import time
from itertools import combinations
import gurobipy as gp
from gurobipy import GRB

# global variables
n,k = None, None

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


def read_file(filename, n_points):
    arq = open(filename,"r")
    points1, points2 = [],[]
    for _ in range(n_points):
        x1,y1,x2,y2 = map(int,arq.readline().split())
        points1.append((x1,y1))
        points2.append((x2,y2))
    return points1, points2


def print_solution(model, dist1, dist2, edges1, edges2):
    tour_tsp1 = subtour(model.getAttr('X', edges1))
    assert len(tour_tsp1) == n

    print('\n')
    print('TSP_1:')
    print('Optimal tour tsp1: %s' % str(tour_tsp1))
    print('Optimal cost tsp1: {}'.format(\
        sum(\
            [dist1[max(tour_tsp1[i],tour_tsp1[(i+1)%n]), min(tour_tsp1[i],tour_tsp1[(i+1)%n])]\
            for i in range(n)])))
    print('')

    tour_tsp2 = subtour(model.getAttr('X', edges2))
    assert len(tour_tsp2) == n

    print('TSP_2:')
    print('Optimal tour tsp2: %s' % str(tour_tsp2))
    print('Optimal cost tsp2: {}'.format(\
        sum(\
            [dist2[max(tour_tsp2[i],tour_tsp2[(i+1)%n]), min(tour_tsp2[i],tour_tsp2[(i+1)%n])]\
            for i in range(n)])))
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
    assert count_k >= k

    print("count_k: {} checked! =)".format(count_k))
    print("Total optimal cost: {}".format(model.ObjVal))



def main():
    # Parse argument
    if len(sys.argv) < 4:
        print('Usage: tsp.py npoints k_paramter name_file')
        sys.exit(1)

    global n,k
    n = int(sys.argv[1])
    k = int(sys.argv[2])
    name_file = str(sys.argv[3])

    print("n = {}".format(n))
    print("k = {}".format(k))

    points1, points2 = read_file(name_file, n)


    # Dictionary of Euclidean distance between each pair of points
    dist1 = {(i, j):
            math.ceil(math.sqrt(sum((points1[i][w]-points1[j][w])**2 for w in range(2))))
            for i in range(n) for j in range(i)}

    dist2 = {(i, j):
            math.ceil(math.sqrt(sum((points2[i][w]-points2[j][w])**2 for w in range(2))))
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
            # m.addConstr(edges1[i,j] + edges2[i,j] >= 2 * duplication[i,j])
            m.addConstr(edges1[i,j] >= duplication[i,j])
            m.addConstr(edges2[i,j] >= duplication[i,j])

    # Optimize model
    m._edges1 = edges1
    m._edges2 = edges2
    m.Params.LazyConstraints = 1

    start_time = time.time()
    m.optimize(subtourelim_updated)
    end_time = time.time()

    print_solution(m, dist1, dist2, edges1, edges2)

    print("Seconds to run the model: {}\n".format((end_time - start_time)))

if __name__ == "__main__":
    main()