export default function CourseScoreTable({ courses }) {
  return (
    <div>
      <h2>رتبه‌بندی دروس پیشنهادی</h2>

      <table className="schedule-table">
        <thead>
          <tr>
            <th>درس</th>
            <th>امتیاز</th>
            <th>دلایل</th>
          </tr>
        </thead>

        <tbody>
          {courses?.map((course) => (
            <tr key={course.course_id}>
              <td>
                {course.course_code} - {course.course_title}
              </td>

              <td>{course.score}</td>

              <td>
                <ul>
                  {course.reasons.map((reason, index) => (
                    <li key={index}>{reason}</li>
                  ))}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}