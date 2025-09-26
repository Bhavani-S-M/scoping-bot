import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function TimelineChart({ timeline }) {
  // Transform timeline [{ name, start, end }] → stacked data
  const data = timeline.map((t) => ({
    name: t.name,
    offset: t.start - 1, // invisible offset before task starts
    duration: t.end - t.start + 1, // actual visible duration
  }));

  return (
    <div className="bg-white p-4 shadow rounded overflow-x-auto">
      <h2 className="font-semibold mb-2">Timeline (Gantt-style)</h2>
      <BarChart
        width={700}
        height={50 + data.length * 40}
        data={data}
        layout="vertical"
        margin={{ top: 20, right: 30, left: 100, bottom: 20 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" label={{ value: "Days", position: "insideBottom" }} />
        <YAxis dataKey="name" type="category" width={100} />
        <Tooltip />
        {/* Invisible offset bar */}
        <Bar dataKey="offset" stackId="a" fill="transparent" />
        {/* Actual duration bar */}
        <Bar dataKey="duration" stackId="a" fill="#4F81BD" />
      </BarChart>
    </div>
  );
}
