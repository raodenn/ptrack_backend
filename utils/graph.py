from collections import deque

def connected_components(graph):
    components = []
    vis = set()

    for node in graph:
        if node not in vis:
            component = []
            q = deque([node])
            vis.add(node)
            component.append(node)

            while q:
                curr = q.popleft()
                for neighbour in graph.get(curr,[]):
                    if neighbour not in vis:
                        vis.add(neighbour)
                        q.append(neighbour)
                        component.append(neighbour)

        if component:
            components.append(component)

    return components

 