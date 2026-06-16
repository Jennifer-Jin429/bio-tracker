const { createApp, ref, computed, onMounted } = Vue;
const API_BASE = '';
const app = createApp({
  setup() {
    const view = ref('dashboard');
    const classes = ref([]);
    const currentClassId = ref(null);
    const currentClassName = ref('');
    const students = ref([]);
    const todayHomework = ref(null);
    const homeworkTitle = ref('');
    const parseText = ref('');
    const parseResult = ref(null);
    const todos = ref([]);
    const todoFilter = ref('all');
    const dictations = ref([]);
    const showDictationForm = ref(false);
    const dictationForm = ref({ date: '', title: '', students: '' });
    const overview = ref({ today_missing: 0, today_empty: 0, today_sick: 0, pending_correct: 0, pending_dictation: 0, overdue_total: 0, today_hw_id: null });
    const riskStudents = ref([]);
    const todayDate = new Date().toISOString().split('T')[0];
    const todayTodos = computed(() => todos.value.filter(t => t.date_group === '今天'));
    const filteredTodos = computed(() => {
      if (todoFilter.value === 'all') return todos.value;
      return todos.value.filter(t => t.type === todoFilter.value);
    });
    const groupedTodos = computed(() => {
      const groups = {};
      const order = ['今天', '昨天', '前天', '更早'];
      for (const item of filteredTodos.value) {
        if (!groups[item.date_group]) groups[item.date_group] = [];
        groups[item.date_group].push(item);
      }
      const result = [];
      for (const name of order) {
        if (groups[name]) result.push({ name, items: groups[name] });
      }
      return result;
    });
    async function fetchClasses() {
      const res = await fetch(`${API_BASE}/api/classes`);
      classes.value = await res.json();
      if (classes.value.length > 0 && !currentClassId.value) {
        currentClassId.value = classes.value[0].id;
        currentClassName.value = classes.value[0].name;
      }
    }
    function changeClass() {
      const cls = classes.value.find(c => c.id === currentClassId.value);
      if (cls) currentClassName.value = cls.name;
      loadData();
    }
    async function loadData() {
      if (!currentClassId.value) return;
      await fetchStudents();
      await fetchHomework();
      await fetchTodos();
      await fetchDictations();
      await fetchOverview();
      await fetchRisk();
    }
    async function fetchStudents() {
      const res = await fetch(`${API_BASE}/api/students?class_id=${currentClassId.value}`);
      students.value = await res.json();
    }
    async function fetchHomework() {
      const res = await fetch(`${API_BASE}/api/homework?class_id=${currentClassId.value}&date=${todayDate}`);
      const data = await res.json();
      if (data.length > 0) { todayHomework.value = data[0]; homeworkTitle.value = data[0].title; }
      else { todayHomework.value = null; }
    }
    async function createHomework() {
      const title = prompt('请输入作业名称:', '生物练习');
      if (!title) return;
      const res = await fetch(`${API_BASE}/api/homework`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date: todayDate, class_id: currentClassId.value, title, remark: '' })
      });
      if (res.ok) await fetchHomework();
    }
    async function saveHomeworkTitle() { alert('作业名称已保存（演示）'); }
    async function updateDetail(d) {
      await fetch(`${API_BASE}/api/homework/${todayHomework.value.id}/details/${d.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student_id: d.student_id, submit_status: d.submit_status, review_status: d.review_status, review_note: d.review_note, correction_status: d.correction_status })
      });
    }
    async function doParse() {
      if (!todayHomework.value) { alert('请先创建今日作业'); return; }
      const res = await fetch(`${API_BASE}/api/parse`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: parseText.value, class_id: currentClassId.value, homework_id: todayHomework.value.id })
      });
      parseResult.value = await res.json();
      await fetchHomework(); await fetchTodos(); await fetchOverview();
    }
    function addHint(text) { parseText.value = parseText.value ? parseText.value + '，' + text : text; }
    async function fetchTodos() {
      const res = await fetch(`${API_BASE}/api/todos?class_id=${currentClassId.value}`);
      todos.value = await res.json();
    }
    async function resolveTodo(item) {
      let action = '已补交';
      if (item.type === '待订正') action = '已订正';
      if (item.type === '待补做') action = '已补做';
      if (item.type === '待重默') action = '已重默';
      const itemType = item.dictation_id ? 'dictation' : 'homework';
      const itemId = item.dictation_id || item.homework_detail_id;
      await fetch(`${API_BASE}/api/todos/resolve`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_type: itemType, item_id: itemId, action })
      });
      await loadData();
    }
    async function fetchDictations() {
      const res = await fetch(`${API_BASE}/api/dictations?class_id=${currentClassId.value}`);
      dictations.value = await res.json();
    }
    async function saveDictation() {
      const lines = dictationForm.value.students.split('\n').filter(l => l.trim());
      for (const line of lines) {
        const match = line.match(/(\d+)号[：:]?(.*)/);
        if (!match) continue;
        const studentNo = match[1].trim();
        const errorContent = match[2].trim();
        const student = students.value.find(s => s.student_no === studentNo);
        if (!student) continue;
        await fetch(`${API_BASE}/api/dictations`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ date: dictationForm.value.date, class_id: currentClassId.value, title: dictationForm.value.title, student_id: student.id, error_content: errorContent, remark: '' })
        });
      }
      showDictationForm.value = false;
      dictationForm.value = { date: '', title: '', students: '' };
      await fetchDictations(); await fetchTodos();
    }
    async function resolveDictation(d) {
      await fetch(`${API_BASE}/api/dictations/${d.id}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: '已重默通过', retest_date: todayDate })
      });
      await fetchDictations(); await fetchTodos();
    }
    async function fetchOverview() {
      const res = await fetch(`${API_BASE}/api/stats/overview?class_id=${currentClassId.value}`);
      overview.value = await res.json();
    }
    async function fetchRisk() {
      const res = await fetch(`${API_BASE}/api/stats/risk?class_id=${currentClassId.value}`);
      riskStudents.value = await res.json();
    }
    function getRowStyle(d) {
      if (d.submit_status === '没交') return 'background:#fef2f2';
      if (d.submit_status === '没做') return 'background:#fff7ed';
      if (d.submit_status === '病假') return 'background:#f0f9ff';
      return '';
    }
    function getItemClass(item) {
      if (item.type === '待补交') return 'urgent';
      if (item.type === '待补做') return 'warning';
      if (item.type === '待订正') return 'warning';
      if (item.type === '待重默') return 'urgent';
      return '';
    }
    function getAvatarColor(type) {
      const map = { '待补交': '#dc2626', '待补做': '#ea580c', '待订正': '#ca8a04', '待重默': '#7c3aed', '抄袭嫌疑': '#7c3aed' };
      return map[type] || '#2563eb';
    }
    function getBadgeClass(type) {
      const map = { '待补交': 'badge-red', '待补做': 'badge-orange', '待订正': 'badge-yellow', '待重默': 'badge-purple', '抄袭嫌疑': 'badge-purple' };
      return map[type] || 'badge-gray';
    }
    function getGroupBadgeClass(name) {
      if (name === '今天') return '';
      if (name === '昨天') return 'warning';
      return 'urgent';
    }
    function getParseStatusStyle(action) {
      const map = { '没交': 'background:#fee2e2;color:#991b1b', '没做': 'background:#ffedd5;color:#9a3412', '病假': 'background:#e0f2fe;color:#075985', '已交': 'background:#dcfce7;color:#166534', '漏做': 'background:#ffedd5;color:#9a3412', '需订正': 'background:#fef3c7;color:#92400e' };
      return map[action] || '';
    }
    onMounted(async () => {
      await fetchClasses();
      await loadData();
      dictationForm.value.date = todayDate;
    });
    return {
      view, classes, currentClassId, currentClassName, students,
      todayHomework, homeworkTitle, parseText, parseResult,
      todos, todoFilter, dictations, showDictationForm, dictationForm,
      overview, riskStudents, todayDate, todayTodos, filteredTodos, groupedTodos,
      changeClass, createHomework, saveHomeworkTitle, updateDetail,
      doParse, addHint, resolveTodo, saveDictation, resolveDictation,
      getRowStyle, getItemClass, getAvatarColor, getBadgeClass, getGroupBadgeClass, getParseStatusStyle
    };
  }
});
app.mount('#app');
