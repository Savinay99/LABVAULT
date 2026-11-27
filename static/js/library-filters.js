(() => {
  const programme = document.querySelector("#id_programme");
  const year = document.querySelector("#id_year");
  const semester = document.querySelector("#id_semester");
  const school = document.querySelector("#id_school");
  const subject = document.querySelector("#id_curriculum_subject");
  const type = document.querySelector("#id_resource_type");
  const source = document.querySelector("#id_source");
  if (!programme || !year || !semester || !subject) return;

  const selected = (select) => select.value;
  const setOptions = (select, values, firstLabel, selectedValue, labelFor, allowUnverified = false) => {
    select.replaceChildren(new Option(firstLabel, ""));
    for (const item of values) {
      const value = typeof item === "object" ? String(item.value ?? item.id) : String(item);
      const label = typeof item === "object" ? labelFor(item) : labelFor(value);
      select.add(new Option(label, value));
    }
    if (allowUnverified && selectedValue && !values.some((item) => String(typeof item === "object" ? (item.value ?? item.id) : item) === String(selectedValue))) {
      const label = select === year ? `Year ${selectedValue} · not verified` : `Semester ${selectedValue} · not verified`;
      const option = new Option(label, String(selectedValue));
      option.disabled = true;
      select.add(option);
    }
    if (selectedValue && [...select.options].some((option) => option.value === String(selectedValue))) {
      select.value = String(selectedValue);
    }
  };

  let generation = 0;
  const refresh = async ({ reset = false } = {}) => {
    const requestId = ++generation;
    const keep = {
      school: reset ? "" : selected(school),
      year: reset ? "" : selected(year),
      semester: reset ? "" : selected(semester),
      subject: reset ? "" : selected(subject),
      type: reset ? "" : selected(type),
      source: reset ? "" : selected(source),
    };
    const endpoint = new URL(programme.dataset.optionsUrl, window.location.origin);
    if (programme.value) endpoint.searchParams.set("programme", programme.value);
    if (keep.year) endpoint.searchParams.set("year", keep.year);
    if (keep.semester) endpoint.searchParams.set("semester", keep.semester);
    try {
      const response = await fetch(endpoint, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      if (!response.ok) return;
      const data = await response.json();
      if (requestId !== generation) return;
      if (school) setOptions(school, data.schools, "All Schools / Areas", keep.school, (value) => value);
      setOptions(year, data.years, "All Years", keep.year, (value) => `Year ${value}`, !reset);
      setOptions(semester, data.semesters, "All Semesters", keep.semester, (value) => `Semester ${value}`, !reset);
      setOptions(subject, data.subjects, "All curriculum subjects", keep.subject, (item) => item.official_code ? `${item.official_code} · ${item.subject_name}` : item.subject_name);
      if (type) setOptions(type, data.resource_types, "All Resource Types", keep.type, (item) => item.label);
      if (source) setOptions(source, data.sources, "All Sources", keep.source, (value) => value);
    } catch (error) {
      // Keep the server-rendered options usable if the dependent request is unavailable.
      console.warn("Library filter options could not be refreshed.");
    }
  };

  programme.addEventListener("change", () => refresh({ reset: true }));
  year.addEventListener("change", () => {
    semester.value = "";
    subject.value = "";
    refresh();
  });
  semester.addEventListener("change", () => {
    subject.value = "";
    refresh();
  });
  refresh();
})();
