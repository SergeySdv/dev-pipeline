// Temporary file to verify D3 types resolve correctly
import * as d3 from "d3";
import { graphStratify } from "d3-dag";

// Test d3 types
const scale = d3.scaleLinear().domain([0, 100]).range([0, 500]);
const result: number = scale(50);

// Test d3-dag types
const data = [
  { id: "a", parentIds: [] as string[] },
  { id: "b", parentIds: ["a"] },
];
const stratify = graphStratify();
const dag = stratify(data);

export { dag,result, scale };
