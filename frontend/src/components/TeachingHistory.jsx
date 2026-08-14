export default function TeachingHistory({ history }) {
  return (
    <div className="teaching-history">
      <h2>📋 سوابق تدریس</h2>
      <div className="table-responsive">
        <table className="course-table">
          <thead>
            <tr>
              <th>استاد</th>
              <th>درس</th>
              <th>ترم</th>
              <th>سال</th>
              <th>تعداد دانشجو</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan="5" className="empty-state">
                  سابقه تدریسی موجود نیست
                </td>
              </tr>
            ) : (
              history.map((item, index) => (
                <tr key={index}>
                  <td>{item.professor}</td>
                  <td>{item.course}</td>
                  <td>{item.semester}</td>
                  <td>{item.year}</td>
                  <td>{item.students}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}