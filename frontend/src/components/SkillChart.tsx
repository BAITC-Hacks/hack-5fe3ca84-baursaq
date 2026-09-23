import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Text, Tooltip, XAxis, YAxis } from 'recharts'

function SkillTick({ x = 0, y = 0, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  return <Text x={x - 6} y={y} width={122} textAnchor="end" verticalAnchor="middle" fontSize={11} lineHeight={14} fill="#33443a">
    {payload?.value ?? ''}
  </Text>
}

export default function SkillChart({ data }: { data: Array<{ name: string; count: number }> }) {
  return <div className="skill-chart" style={{ height: Math.max(240, data.length * 56 + 40) }} role="img" aria-label={data.map(item => `${item.name}: ${item.count} сотрудников`).join('; ')}>
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ left: 0, right: 16 }}>
        <CartesianGrid stroke="#edf1ed" horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={{ fill: '#657b6e', fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={138} interval={0} tick={<SkillTick />} />
        <Tooltip />
        <Bar dataKey="count" fill="#00805f" maxBarSize={20} radius={[0, 6, 6, 0]} name="Сотрудников" />
      </BarChart>
    </ResponsiveContainer>
  </div>
}
