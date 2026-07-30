# Feature Specification: Project Management (PM)

> **Feature:** 7.6 Project Management  
> **Jira Epic:** [GBX03-9](https://globee-software-ecommerce.atlassian.net/browse/GBX03-9)  
> **Spec:** [spec.md](spec.md)

---

## PM-US-01: Create a Project

> **Jira Story:** [GBX03-19](https://globee-software-ecommerce.atlassian.net/browse/GBX03-19)

### User Scenarios & Testing *(mandatory)*

As a **PM**, I want to register a new **Project** under its owning **Business Unit** so that the work can be reviewed, approved by **DM**, and have its staffing, skills, and finances planned and tracked from its initial `New` status.

**Acceptance Criteria**:

**AC-01: Successfully create a Project with all mandatory inputs**  
**Given** a PM user accesses the Create Project form,  
**When** the user provides a valid Code, Name, a PM and an assigned DM — each a valid actor, i.e. an Employee holding an active User account with the matching role (PM role for the PM, DM role for the assigned DM) — Start Date, owning Business Unit, and at least one required Skill, and submits the form,  
**Then** the system creates the Project with Status automatically set to New, displays a success confirmation, and the new record is immediately available in the system.

**AC-02: Reject submission when Code is already in use**  
**Given** a Project with Code "PJ_2026_001" already exists in the system,  
**When** a PM submits a new Project using the same Code,  
**Then** the system rejects the submission and displays an error indicating the Code must be unique.

**AC-03: Reject submission when Name is already in use**  
**Given** a Project with Name "SFCC Phase 1" already exists in the system,  
**When** a PM submits a new Project using the same Name,  
**Then** the system rejects the submission and displays an error indicating the Name must be unique.

**AC-04: Reject submission when the owning Business Unit is missing or inactive**  
**Given** the Business Unit selected for the new Project does not exist or is Inactive,  
**When** a PM submits the Create Project form referencing that Business Unit,  
**Then** the system rejects the submission and displays an error indicating the Business Unit must exist and be Active.

**AC-05: Reject submission when the PM is duplicated in the Project Lead list**  
**Given** a PM user is completing the Create Project form,  
**When** the user selects themselves (the same Employee designated as PM) as a Project Lead and submits the form,  
**Then** the system rejects the submission and displays an error indicating the PM must not also appear in the Project Lead list.

**AC-06: Reject submission when Start Date is later than End Date**  
**Given** a PM user provides both a Start Date and an End Date,  
**When** the End Date entered is earlier than the Start Date and the form is submitted,  
**Then** the system rejects the submission and displays a validation error.

**AC-07: Reject submission when no required Skill is selected**  
**Given** a PM user is completing the Create Project form,  
**When** the user submits the form without selecting at least one Skill,  
**Then** the system rejects the submission and displays an error indicating at least one Skill is required.

**AC-08: Deny access to non-PM users**  
**Given** a user whose role is ADMIN, HR, FA, or DM,  
**When** the user attempts to access the Create Project form or submits a creation request,  
**Then** the system denies access and no Project is created.

**AC-09: Record a creation audit event on success**  
**Given** an authenticated PM,  
**When** they successfully create a Project,  
**Then** the system records an audit entry capturing the actor, the timestamp, and the full details of the newly created Project.

**AC-10: Reject submission when Code format is invalid**  
**Given** a PM user is on the Create Project form,  
**When** the user enters a Code containing lowercase letters, spaces, or any character other than uppercase letters, numbers, and underscores,  
**Then** the system displays a field-level validation error and prevents the form from being submitted.

**AC-11: Reject submission when the assigned DM is missing or the PM/DM selection is not a valid actor**  
**Given** a PM user is completing the Create Project form,  
**When** the user submits the form without selecting an assigned DM, or selects a PM or an assigned DM that references an Employee without an active User account holding the corresponding role,  
**Then** the system rejects the submission and displays an error indicating that an assigned DM is required, or that the selected PM/DM must be an Employee with an active User account in the matching role.

**AC-12: Compute and display planning-line sums before saving**  
**Given** a PM user is completing the Create Project form and adds one or more planning lines, each choosing a Role from the configured value list and manually entering a unit price and a number of people,  
**When** the user reviews the form before submitting,  
**Then** the system displays the resulting sums as Planned Effort (MM) and Forecast Income, and, upon submission, stores the planning lines together with those computed values as part of the Project.

### Edge Cases

**EC-01**: **Optional fields omitted** — when Project Lead, End Date, Project Type, Business Domain, Forecast Income (and its currency), Planned Effort, Description, and all Customer contact fields are omitted, creation still succeeds because none of them is mandatory.

**EC-02**: **Non-positive Forecast Income or Planned Effort** — when Forecast Income or Planned Effort is provided as zero or a negative value, the system rejects the submission with a validation error.

**EC-03**: **Free-text field exceeds maximum length** — when Description exceeds 1000 characters (SRS PM-FR-12), Customer Department exceeds 200 characters (SRS PM-FR-18), Customer PIC exceeds 200 characters (SRS PM-FR-19), Customer Email exceeds 255 characters (SRS PM-FR-20), Customer Phone Number exceeds 50 characters (SRS PM-FR-21), or Technical Information exceeds 2000 characters (SRS PM-FR-23), the system rejects the submission with a validation error.

**EC-04**: **Project Type or Business Domain not from the active configured list** — when the submitted Project Type or Business Domain value is inactive or absent from its configured value list, the system rejects the submission with a validation error.

**EC-05**: **Concurrent duplicate submission** — when two PM users simultaneously submit a Project with the same Code or Name, only the first succeeds; the second receives a conflict error.

**EC-06**: **Code with whitespace** — when a Code is submitted with leading or trailing whitespace, the system treats it as **invalid format** and rejects it with a **validation error**.

**EC-07**: **Non-positive planning-line values** — when a planning line's unit price or number of people is zero or a negative value, the system rejects the submission with a validation error.

### Requirements *(mandatory)*

#### Functional Requirements

- **FR-01**: The system must **allow** authenticated **PM** users to **access** a form for **creating** a new Project.
- **FR-02**: The system must **accept** the following mandatory inputs: **Code**, **Name**, **PM**, assigned **DM**, **Start Date**, owning **Business Unit**, and at least one required **Skill** (SRS PM-FR-01, PM-FR-02, PM-FR-04, PM-FR-06, PM-FR-09, PM-FR-27; §2.3).
- **FR-03**: The system must **accept** the following optional inputs when provided: **Project Lead(s)**, **End Date**, **Project Type**, **Business Domain**, **Forecast Income** and its currency, **Planned Effort**, **Description**, **Customer Name**, **Customer Department**, **Customer PIC**, **Customer Email**, **Customer Phone Number**, and **Technical Information** (SRS PM-FR-03, PM-FR-05, PM-FR-07, PM-FR-10 through PM-FR-13, PM-FR-15, PM-FR-17 through PM-FR-21, PM-FR-23).
- **FR-04**: The system must **automatically set** Status to **New** on every new Project; PM users do not set Status at creation time (SRS PM-FR-08).
- **FR-05**: The system must **validate** that **Code** is **unique** across all existing Projects (SRS PM-FR-01).
- **FR-06**: The system must **validate** that **Name** is **unique** across all existing Projects (SRS PM-FR-02).
- **FR-07**: The system must **validate** that the selected **Business Unit** exists and is **Active** (SRS BR-01, PM-FR-09).
- **FR-08**: The system must **validate** that the selected **PM** references an Employee holding an **active User account** with the **PM role** (SRS PM-FR-04).
- **FR-09**: The system must **validate** that the PM is **not duplicated** in the Project Lead list, and that the Project Lead list itself contains **no duplicate entries** (SRS BR-03, PM-FR-05).
- **FR-10**: The system must **support** selecting Project Leads **filtered** to Employees whose Title is `Project Lead`; a selected Project Lead is validated against Employee data only. Unlike the PM and assigned DM (FR-08, FR-22), Project Leads are **informational**, perform **no system actions** in this feature, and are **not required** to hold a User account (SRS PM-FR-05).
- **FR-11**: The system must **validate** that **Start Date** is not later than **End Date**, when End Date is provided (SRS PM-FR-06, PM-FR-07).
- **FR-12**: The system must **validate** that at least **one Skill** is selected as a required Skill for the Project and that each selected Skill exists in the seeded Skill reference catalog (SRS §2.3, PM-FR-14).
- **FR-13**: The system must **validate** that **Forecast Income** and **Planned Effort**, when provided, are **greater than 0** (SRS PM-FR-11, PM-FR-15).
- **FR-14**: The system must **validate** that, when provided, **Description** does not exceed **1000 characters** (SRS PM-FR-12), **Customer Department** does not exceed **200 characters** (SRS PM-FR-18), **Customer PIC** does not exceed **200 characters** (SRS PM-FR-19), **Customer Email** does not exceed **255 characters** (SRS PM-FR-20), **Customer Phone Number** does not exceed **50 characters** (SRS PM-FR-21), and **Technical Information** does not exceed **2000 characters** (SRS PM-FR-23).
- **FR-15**: The system must **validate** that the selected **Project Type** and **Business Domain**, when provided, come from their respective **active configured value lists** (SRS PM-FR-03, PM-FR-10).
- **FR-16**: The system must **display** a **field-level validation message** for each invalid or missing required field.
- **FR-17**: The system must **deny** Project creation to any user whose role is **not PM**.
- **FR-18**: The system must **record** a **creation audit event** on success, capturing actor, timestamp, and the full record details.
- **FR-19**: The system must **enforce uniqueness** under **concurrent** creation attempts and persist only one record when duplicate Code or Name values are submitted simultaneously.
- **FR-20**: The system must **display** a **success confirmation** to the PM after the Project is created.
- **FR-21**: The system must **validate** that **Code** contains only **uppercase letters, numbers, and underscores** — no spaces or other characters — and must **prevent** any change to Code once the Project has been created (SRS PM-FR-01).
- **FR-22**: The system must **accept** a mandatory **assigned DM** input and **validate** that the selected DM references an Employee holding an **active User account** with the **DM role** (SRS PM-FR-27).
- **FR-23**: The system must **support** optional **planning lines**, each composed of a Role selected from the shared Data Configuration value list together with a manually entered unit price and a manually entered number of people; the system must **sum** the planning lines to produce **Planned Effort (MM)** and **Forecast Income**. When no planning lines are entered, the system must continue to **accept** Planned Effort and Forecast Income as **direct numeric entries** (SRS PM-FR-11, PM-FR-15). Forecast Income **currency** defaults to `VND` and is **not selectable** at creation (SRS PM-FR-17).
- **FR-24**: The system must **validate** that each planning line's **unit price** and **number of people** are **greater than 0**.

#### Business Rules

- **BR-01**: A Project must belong to exactly one Business Unit, which must exist and be Active before assignment (SRS BR-01).
- **BR-02**: A Project must have exactly one PM; the PM must not be duplicated in the Project Lead list (SRS BR-03).
- **BR-03**: Project Leads are optional and are selected from Employees whose Title is `Project Lead`; duplicate Project Leads within the same Project are not allowed.
- **BR-04**: Every newly created Project starts in `New` status; subsequent lifecycle transitions follow the canonical Project state model and are outside this story (SRS BR-04).
- **BR-05**: A Project must reference at least one required Skill (SRS §2.3).
- **BR-06**: Start Date must not be later than End Date when an End Date is provided.
- **BR-07**: Forecast Income and Planned Effort, when provided, must be greater than 0.
- **BR-08**: Project Type and Business Domain values must be selected from their respective active configured value lists; inactive or unlisted values are not permitted (SRS BR-07, PM-FR-10).
- **BR-09**: A Project has exactly one assigned DM; only the assigned DM may later approve or reject the Project or its Project Update Requests. Approval itself is outside this story (SRS shared project business rules). The PM and the assigned DM must each hold an active User account with the matching role, so they can perform their later lifecycle actions (manage; approve/reject).

#### Key Entities

- **Project**: A business project tracked through approval, staffing, cost, and lifecycle states. Owned by exactly one Business Unit; created with Status `New`.
- **Business Unit**: An organizational unit that owns the Project; must be Active to be eligible for assignment.
- **Employee**: Globee's business/HR record for a person, maintained for assignment, capacity, and HR tracking; source of candidates for the PM, assigned DM, and Project Lead selections. Distinct from a User, the technical login account an Employee may optionally hold (at most one, per SRS §2.3). The PM and assigned DM fields are **actor references**: each must be an Employee linked to an active User account holding the matching role (PM, DM). Project Lead entries are **informational only** and require no User account.
- **Skill**: Reusable skill reference data; a Project requires at least one Skill.

### Success Criteria *(mandatory)*

- **SC-01**: A PM user can create a Project with all mandatory inputs and the record appears with Status `New` immediately after creation.
- **SC-02**: The system prevents creation whenever Code or Name is a duplicate, the Business Unit is missing or inactive, the PM is duplicated in the Project Lead list, Start Date is later than End Date, no Skill is selected, or a numeric or length constraint is violated.
- **SC-03**: Non-PM users cannot create a Project; access is denied at both form-access and submission level.
- **SC-04**: A newly created Project is immediately available in GRM for subsequent review, approval, and staffing, skill, and finance planning.
- **SC-05**: A creation audit entry is recorded for every successful Project creation.
- **SC-06**: A created Project always carries exactly one PM and one assigned DM, and its Forecast Income and Planned Effort equal either directly entered values or the sums of its planning lines.

### Assumptions & Dependencies

- Skill reference data, delivered by prior features, exists before Projects are created.
- Active configured values for Project Type, Business Domain, and planning-line Roles exist before Projects are created; their initial seed values are delivered with this feature.
- Business Units and Employees, including the Employee Title data used to filter Project Lead candidates, already exist as delivered by prior features (Business Unit, Employee Management).
- Authentication and role-based authorization are operational.
- A PM holds the organizational authority to register new Projects under an owning Business Unit.
