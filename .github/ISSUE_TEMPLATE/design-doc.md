---
name: Design document
about: Create a proposal for a feature which includes substantial architectural work.
title: ''
labels: design-doc, feature
assignees: ''

---
# UCC Design Doc

<!-- Template to use for proposing substantial changes to UCC: architecture changes, major refactoring, new modules, etc. -->

## Motivation
Why should we build this? What problems are we trying to address?


## Goals
What are in-scope goals for this project? These should be high-level, but specific enough to map onto sub-issues. How will we know we've achieved these goals?


## Non-Goals
What is out-of-scope for this project? What possible tools are we NOT building and which possible use cases are we NOT covering?


## User Experience/Workflows to Support
Which kinds of users are we targeting with this project? Which of their workflows do we plan to support?  


## Proposal

### Architecture

1. A written description of the high-level architecture of your new proposed module(s),
2. An architecture diagram showing the flow of a user's program through UCC and your new proposed modules. 

Describe each of the components and dataflow between them as follows...

---

### Component 1
> Describe component 1.  

##### API
How will existing components of UCC call into this component? What data will they receive back?

##### Code snippet
If appropriate, give an example of how a user would interact with this component.

```
my_object = api_call(foo)
```

##### Specification
If this component will be interacting with any standardized interfaces, you may need a spec to describe it. 

##### Design Questions
What do we need to know or decide in order to design this component well?

1. 
2. 
3. 

---

### Component 2
<!-- Component 3... Component N  -->
.
.
.

## Open questions
What areas of design still need to be fleshed out or need additional feedback to move forward? 


## Alternatives

Survey the existing tools out there which do similar or related tasks to your project. Give a brief description of each tool, how they differ or overlap in scope with your own, and why you may or may not want to use them.


## FAQ
If you imagined pitching this idea to a colleague, what questions would they ask you? 


## Reasons not to do this (now)

What are good reasons to put off doing this? Are user needs too uncertain? Is there already a crowded ecosystem of work in this space that we need to understand? Does the technology it aims to integrate need more maturity? 
