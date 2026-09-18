"""Extract the pencil path from the masked image as an ordered polyline
in pixel coordinates, bridging small drawing gaps.

Approach:
1. Build a binary mask for the gray path (excluding grid pixels).
2. Skeletonize.
3. For each connected component of the skeleton, build a pixel-adjacency
   graph and extract the "diameter path" (double sweep BFS) -- this finds
   the longest simple path in the component, which corresponds to the
   real drawn stroke while ignoring short spurious spurs from noise.
4. Discard components whose diameter path is too short (junk).
5. Chain the remaining component paths end-to-end (nearest endpoints)
   to produce one continuous ordered polyline for the whole path,
   bridging the pencil-lift gaps with straight segments.
"""
import cv2
import numpy as np
import networkx as nx
from skimage.morphology import skeletonize

MASKED = "20260917_175649_masked.png"
MIN_DIAMETER_PX = 300  # discard skeleton components with shorter main path (junk)


def path_mask(im):
    im = im.astype(np.int16)
    R = im[:, :, 2]
    nonwhite = R < 245
    mask = (nonwhite & (R < 178)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return mask


def skeleton_graph(skel):
    ys, xs = np.where(skel)
    pts = set(zip(xs.tolist(), ys.tolist()))
    G = nx.Graph()
    G.add_nodes_from(pts)
    for (x, y) in pts:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                q = (x + dx, y + dy)
                if q in pts:
                    w = 1.0 if dx == 0 or dy == 0 else 1.4142135623730951
                    G.add_edge((x, y), q, weight=w)
    return G


def diameter_path(G):
    """Double-sweep BFS/Dijkstra to find the longest shortest-path (the
    main centerline) within a (possibly tree-like) connected component."""
    any_node = next(iter(G.nodes))
    lengths = nx.single_source_dijkstra_path_length(G, any_node)
    a = max(lengths, key=lengths.get)
    lengths2, paths2 = nx.single_source_dijkstra(G, a)
    b = max(lengths2, key=lengths2.get)
    path = paths2[b]
    return path, lengths2[b]


def main():
    im = cv2.imread(MASKED)
    mask = path_mask(im)
    cv2.imwrite("dbg_path_mask_final.png", mask)

    skel = skeletonize(mask > 0)
    print("skeleton px", skel.sum())

    G = skeleton_graph(skel)
    comps = list(nx.connected_components(G))
    print("num components", len(comps))

    segments = []
    for comp in comps:
        if len(comp) < 5:
            continue
        sub = G.subgraph(comp)
        path, length = diameter_path(sub)
        if length < MIN_DIAMETER_PX:
            continue
        segments.append(np.array(path, dtype=float))  # (x,y) pairs

    segments.sort(key=len, reverse=True)
    print("num real segments", len(segments))
    for s in segments:
        print("  segment len(px path)=", len(s), "endpoints", s[0], s[-1])

    # chain segments end-to-end via nearest-endpoint greedy matching
    remaining = segments[:]
    chain = remaining.pop(0)
    while remaining:
        chain_ends = [chain[0], chain[-1]]
        best = None
        for i, seg in enumerate(remaining):
            for seg_flip, seg_pts in ((False, seg), (True, seg[::-1])):
                for chain_end_idx, ce in enumerate(chain_ends):
                    d = np.hypot(*(seg_pts[0] - ce))
                    if best is None or d < best[0]:
                        best = (d, i, chain_end_idx, seg_flip)
        d, i, chain_end_idx, seg_flip = best
        seg = remaining.pop(i)
        if seg_flip:
            seg = seg[::-1]
        if chain_end_idx == 0:
            chain = np.concatenate([seg[::-1], chain])
        else:
            chain = np.concatenate([chain, seg])
        print(f"bridged gap of {d:.1f}px")

    print("final polyline points:", len(chain))
    np.save("path_polyline.npy", chain)

    # visualize
    vis = im.copy()
    for i in range(len(chain) - 1):
        p1 = tuple(chain[i].astype(int))
        p2 = tuple(chain[i + 1].astype(int))
        cv2.line(vis, p1, p2, (0, 0, 255), 2)
    cv2.imwrite("dbg_path_polyline.png", vis)


if __name__ == "__main__":
    main()
