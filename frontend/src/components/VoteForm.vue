<template>
  <div class="vote-form">
    <h3>نظرسنجی ارائه دروس</h3>
    <div class="form-group">
      <label>ترم:</label>
      <input v-model="term" type="text" placeholder="مثال: 1402-1" />
    </div>

    <div v-for="course in courses" :key="course.id" class="vote-item">
      <span>{{ course.name }}</span>
      <button @click="vote(course.id, 'like')" :disabled="loading">👍 لایک</button>
      <button @click="vote(course.id, 'request')" :disabled="loading">📝 درخواست ارائه</button>
      <span class="stats">لایک: {{ getVotes(course.id, 'like') }} | درخواست: {{ getVotes(course.id, 'request') }}</span>
    </div>

    <p v-if="message" class="message">{{ message }}</p>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      term: '',
      courses: [],
      votes: {},
      loading: false,
      message: ''
    };
  },
  mounted() {
    this.fetchCourses();
  },
  methods: {
    async fetchCourses() {
      try {
        const res = await axios.get('/api/courses');
        this.courses = res.data;
        this.fetchVoteStats();
      } catch (err) {
        console.error('Error fetching courses:', err);
      }
    },
    async fetchVoteStats() {
      for (const course of this.courses) {
        try {
          const res = await axios.get(`/api/votes/stats/${course.id}`, {
            params: { term: this.term || '1402-1' }
          });
          this.votes[course.id] = res.data;
        } catch (err) {
          console.error('Error fetching vote stats:', err);
        }
      }
    },
    getVotes(courseId, type) {
      return this.votes[courseId]?.[type] || 0;
    },
    async vote(courseId, type) {
      this.loading = true;
      this.message = '';
      try {
        const studentId = 1; // از احراز هویت دریافت شود
        await axios.post('/api/votes', {
          course_id: courseId,
          vote_type: type,
          term: this.term || '1402-1'
        }, { params: { student_id: studentId } });
        this.message = 'رأی شما با موفقیت ثبت شد!';
        this.fetchVoteStats();
      } catch (err) {
        this.message = 'خطا: ' + (err.response?.data?.detail || err.message);
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>