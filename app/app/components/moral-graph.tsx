import { useEffect, useRef, useState } from "react";
import ValuesCard from "~/components/cards/values-card";
import * as d3 from "d3";
import type { MoralGraph as MoralGraphType } from "~/routes/api.graph";
import type { CanonicalValuesCard } from "@prisma/client";

type Node = MoralGraphType["values"][0]
type Link = MoralGraphType["edges"][0]

function NodeInfoBox({ node, x, y }: { node: Node | null; x: number; y: number }) {
  if (!node) return null

  const boxWidth = 200; // Assume a box width
  const offset = 20; // Offset from the cursor position
  const viewportWidth = window.innerWidth; // Width of the viewport

  // If the box would overflow the right edge of the viewport, 
  // position it to the left of the cursor, otherwise to the right.
  const leftPosition = x + boxWidth + offset > viewportWidth
    ? x - boxWidth - offset
    : x + offset;

  const style = {
    position: "absolute",
    left: leftPosition,
    top: y + offset,
  }

  return (
    <div className="info-box z-50" style={style as any}>
      <ValuesCard card={
        {
          title: node.title,
          instructionsShort: "",
          instructionsDetailed: "",
          evaluationCriteria: node.policies
        }
      } detailsInline />
    </div>
  )
}

function LinkInfoBox({ link, x, y }: { link: Link | null; x: number; y: number }) {
  if (!link) return null

  // const boxWidth = 200; // Assume a box width
  // const offset = 20; // Offset from the cursor position
  // const viewportWidth = window.innerWidth; // Width of the viewport

  // If the box would overflow the right edge of the viewport, 
  // position it to the left of the cursor, otherwise to the right.
  // const leftPosition = x + boxWidth + offset > viewportWidth
  //   ? x - boxWidth - offset
  //   : x + offset;

  const style = {
    position: "absolute",
    // left: leftPosition,
    right: 0,
    top: 0,
  }

  // self.input_value_was_really_about = input_value_was_really_about
  // self.clarification = clarification
  // self.mapping = mapping

  return (
    <div className="info-box z-50 h-full overflow-y-scroll" style={style as any} onClick={(e: any) => {
      // Prevent clicks inside of the box from closing it
      e.stopPropagation()
    }}>
      <div className="border-l-2 border-gray-200 px-8 py-4 max-w-md bg-white flex flex-col">
        <p className="text-md font-semibold text-gray-400 mb-4">{link.context}</p>
        {link.metadata?.input_value_was_really_about && (
          <>
            <p className="text-sm font-semibold text-gray-400 mb-1">What was the value really about?</p>
            <p className="text-sm mb-4">{link.metadata.input_value_was_really_about}</p>
          </>
        )}
        {link.metadata?.clarification && (
          <>
            <p className="text-sm font-semibold text-gray-400 mb-1">What was clarified?</p>
            <p className="text-sm mb-4">{link.metadata.clarification}</p>
          </>
        )}
        {link.metadata?.mapping && (
          <>
            <p className="text-sm font-semibold text-gray-400 mb-1">Mappings</p>
            {link.metadata.mapping.map((mapping: {a: string, rationale: string}) => (
              <div key={mapping.a}>
                <p className="text-xs font-semibold text-gray-400 mb-1">{mapping.a}</p>
                <p className="text-sm mb-6">{mapping.rationale}</p>
              </div>
            ))}
          </>
        )}
        <p className="text-sm font-semibold text-gray-400 mb-1">Story</p>
        <p className="text-sm mb-4">{link.story}</p>
      </div>
    </div>
  );
}

interface Link2 {
  source: string | CanonicalValuesCard
  target: string | CanonicalValuesCard
  context: string,
  story: string,
}


export default function MoralGraph({ graph }: { graph: MoralGraphType }) {
  const links = graph.edges.map((edge) => ({
    source: edge.from_id,
    target: edge.to_id,
    context: edge.context,
    story: edge.story,
    metadata: edge.metadata,
  })) satisfies Link2[]

  return <GraphWithInfoBox nodes={graph.values} links={links} />
}

function GraphWithInfoBox({ nodes, links }: { nodes: Node[]; links: Link2[] }) {
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null)
  const [hoveredLink, setHoveredLink] = useState<Link | null>(null)
  const [clickedLink, setClickedLink] = useState<Link | null>(null)

  const [position, setPosition] = useState<{ x: number; y: number }>({
    x: 0,
    y: 0,
  })

  return (
    <div onClick={() => setClickedLink(null)}>
      <Graph nodes={nodes} links={links} setHoveredNode={setHoveredNode} setHoveredLink={setHoveredLink} setClickedLink={setClickedLink} setPosition={setPosition} hoveredLink={hoveredLink} />
      <NodeInfoBox node={(hoveredNode as any)?.data} x={position.x} y={position.y} />
      <LinkInfoBox link={clickedLink ?? hoveredLink} x={position.x} y={position.y} />
    </div>
  )
}

function Graph({ nodes, links, setHoveredNode, setHoveredLink, setClickedLink, setPosition }: { nodes: Node[]; links: Link2[], setHoveredNode: (node: Node | null) => void, setHoveredLink: (link: Link | null) => void, setClickedLink: (link: Link | null) => void, setPosition: (position: { x: number; y: number }) => void }) {
  let hoverTimeout: NodeJS.Timeout | null = null
  const ref = useRef<SVGSVGElement>(null)
  useEffect(() => {
    const svg = d3
      .select(ref.current)
      .attr("width", "100%") // Full-screen width
      .attr("height", "100vh") // Full-screen height
      .attr("zoom", "1")

    svg.selectAll("g > *").remove()
    const g = svg.append("g")

    // Define arrow markers
    svg
      .append("defs")
      .selectAll("marker")
      .data(["end"])
      .enter()
      .append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20) // Adjust position for bigger arrowhead
      .attr("refY", 0)
      .attr("orient", "auto")
      .attr("markerWidth", 4) // Increase size
      .attr("markerHeight", 4) // Increase size
      .attr("xoverflow", "visible")
      .append("svg:path")
      .attr("d", "M 0,-5 L 10,0 L 0,5")

    // Add zoom behavior
    const zoom = d3.zoom().on("zoom", (event: any) => {
      g.attr("transform", event.transform)
    })
    // @ts-ignore
    svg.call(zoom)

    // Create force simulation
    const simulation = d3
      // @ts-ignore
      .forceSimulation<Node, Link>(nodes)
      .force(
        "link",
        // @ts-ignore
        d3
          // @ts-ignore
          .forceLink<Link, Node>(links)
          // @ts-ignore
          .id((d: Node) => d.id)
          .distance(120)
      )
      // @ts-ignore
      .force(
        "charge",
        // @ts-ignore
        d3
          .forceManyBody().strength(-50)

      ) // Weaker repulsion within groups
      .force(
        "center",
        // @ts-ignore
        d3
          .forceCenter(window.innerWidth / 2, window.innerHeight / 2)
          .strength(0.05)
      ) // Weaker central pull

    // Draw links
    const link = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d: any) => {
        return d3.interpolateGreys(1)
      })
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrowhead)") // Add arrowheads
      .on("mouseover", (event: any, d: any) => {
        if (hoverTimeout) clearTimeout(hoverTimeout);
        setHoveredLink(d);
        setHoveredNode(null)
        setPosition({ x: event.clientX, y: event.clientY });
      })
      .on("click", (event: any, d: any) => {
        event.stopPropagation()
        setClickedLink(d)
        setPosition({ x: event.clientX, y: event.clientY });
      })
      .on("mouseout", () => {
        // eslint-disable-next-line react-hooks/exhaustive-deps
        hoverTimeout = setTimeout(() => {
          setHoveredLink(null);
        }, 200); // 200 milliseconds delay
      });

    // Draw edge labels
    const edgeLabels = g
      .append("g")
      .selectAll("text")
      .data(links)
      .enter()
      .append("text")
      .attr("font-size", "8px")
      .attr("fill", "#ccc")
      .attr("text-anchor", "middle")
      .attr("dy", -5)
      .on("mouseover", (event: any, d: any) => {
        if (hoverTimeout) clearTimeout(hoverTimeout);
        setHoveredLink(d);
        setHoveredNode(null)
        setPosition({ x: event.clientX, y: event.clientY });
      })
      .on("click", (event: any, d: any) => {
        event.stopPropagation()
        setClickedLink(d)
        setPosition({ x: event.clientX, y: event.clientY });
      })
      .on("mouseout", () => {
        hoverTimeout = setTimeout(() => {
          setHoveredLink(null);
        }, 200); // 200 milliseconds delay
      });

    // Draw nodes
    const node = g
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 10)
      .attr("fill", "lightgray")
      .on("mouseover", (event: any, d: Node) => {
        if (hoverTimeout) clearTimeout(hoverTimeout)
        setHoveredNode(d)
        setHoveredLink(null)
        setPosition({ x: event.clientX, y: event.clientY })
      })
      .on("mouseout", () => {
        hoverTimeout = setTimeout(() => {
          setHoveredNode(null)
        }, 200) // 200 milliseconds delay
      })
      .call(
        // @ts-ignore
        d3
          .drag() // Make nodes draggable
          .on("start", dragStart)
          .on("drag", dragging)
          .on("end", dragEnd)
      )

    // Draw labels
    const label = g
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d: Node) => d.title)
      .attr("font-size", "10px")

    // Update positions
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y)

      edgeLabels
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2)
        .text((d: any) => d.context)

      node.attr("cx", (d: any) => d.x).attr("cy", (d: any) => d.y)

      label.attr("x", (d: any) => d.x + 15).attr("y", (d: any) => d.y + 4)
    })

    // Drag functions
    function dragStart(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    }

    function dragging(event: any, d: any) {
      d.fx = event.x
      d.fy = event.y
    }

    function dragEnd(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
    }
  }, [nodes, links])
  return <svg ref={ref} style={{ userSelect: "none" }}>
    <g></g>
  </svg>
}