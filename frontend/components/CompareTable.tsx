import type { CompareUI } from '../lib/api';

export default function CompareTable({ ui }: { ui: CompareUI }) {
  return (
    <div className="compare">
      <div className="compare-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col"><span className="sr">Detail</span></th>
              {ui.columns.map((c) => (
                <th scope="col" key={c.id}>
                  <a href={c.url} target="_blank" rel="noopener noreferrer">{c.title}</a>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ui.rows.map((r) => (
              <tr key={r.label}>
                <th scope="row">{r.label}</th>
                {r.values.map((v, i) => <td key={i}>{v}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
